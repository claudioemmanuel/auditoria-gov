"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getCoverageV2Summary, getRadarV2Signals, getRadarV2Summary } from "@/lib/api";
import type { RadarV2SignalItem, RadarV2SummaryResponse, CoverageV2SummaryResponse } from "@/lib/types";
import { formatNumber, relativeTime } from "@/lib/utils";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Calendar,
  CheckCircle2,
  Clock,
  Database,
  FileText,
  LayoutDashboard,
  Network,
  Radar,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
  Users,
  Workflow,
  XCircle,
} from "lucide-react";

// ── Severity config ──────────────────────────────────────────────────────────

const SEV: Record<string, { label: string; dot: string; text: string; border: string; bg: string }> = {
  critical: { label: "Crítico", dot: "bg-error",        text: "text-error",        border: "border-error/30",        bg: "bg-error/5"     },
  high:     { label: "Alto",    dot: "bg-amber",         text: "text-amber",         border: "border-amber/30",         bg: "bg-amber/5"     },
  medium:   { label: "Médio",   dot: "bg-yellow-500",    text: "text-yellow-600",    border: "border-yellow-500/30",    bg: "bg-yellow-500/5"},
  low:      { label: "Baixo",   dot: "bg-info",          text: "text-info",          border: "border-info/30",          bg: "bg-info/5"      },
};

const PIPELINE_CFG: Record<string, { label: string; cls: string; Icon: typeof CheckCircle2 }> = {
  healthy:   { label: "Saudável",  cls: "text-success border-success/30 bg-success/5", Icon: CheckCircle2 },
  attention: { label: "Atenção",   cls: "text-amber   border-amber/30   bg-amber/5",   Icon: AlertTriangle },
  blocked:   { label: "Bloqueado", cls: "text-error   border-error/30   bg-error/5",   Icon: XCircle },
};

// ── Reusable KPI card ────────────────────────────────────────────────────────

function KpiCard({
  label,
  value,
  sub,
  dot,
  loading,
}: {
  label: string;
  value: string | number;
  sub?: string;
  dot?: string;
  loading: boolean;
}) {
  if (loading) {
    return <div className="h-20 rounded-xl border border-border bg-surface-card animate-pulse" />;
  }
  return (
    <div className="rounded-xl border border-border bg-surface-card px-4 py-4">
      <div className="flex items-center gap-1.5 mb-2">
        {dot && <span className={`h-2 w-2 rounded-full ${dot}`} />}
        <p className="font-mono text-[9px] uppercase tracking-widest text-muted">{label}</p>
      </div>
      <p className="font-mono text-2xl font-bold tabular-nums text-primary leading-none">{value}</p>
      {sub && <p className="font-mono text-[10px] text-muted mt-1.5">{sub}</p>}
    </div>
  );
}

// ── Recent signal row ────────────────────────────────────────────────────────

function SignalRow({ item }: { item: RadarV2SignalItem }) {
  const s = SEV[item.severity] ?? SEV.low;
  return (
    <Link
      href={`/signal/${item.id}`}
      className="group flex items-start gap-3 rounded-lg px-3 py-2.5 transition hover:bg-surface-subtle"
    >
      <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${s.dot}`} />
      <div className="min-w-0 flex-1">
        <p className="text-xs font-semibold text-primary truncate leading-snug group-hover:text-accent transition-colors">
          {item.title}
        </p>
        <div className="flex items-center gap-2 mt-0.5 text-[10px] text-muted">
          <span className="font-mono font-bold text-accent">{item.typology_code}</span>
          <span className="flex items-center gap-0.5">
            <Users className="h-2.5 w-2.5" />
            {item.entity_count}
          </span>
          <span className="flex items-center gap-0.5">
            <FileText className="h-2.5 w-2.5" />
            {item.event_count}
          </span>
          {item.has_graph && (
            <span className="flex items-center gap-0.5 text-accent">
              <Network className="h-2.5 w-2.5" />
              grafo
            </span>
          )}
        </div>
      </div>
      <div className="shrink-0 flex flex-col items-end gap-1">
        <span className={`inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[9px] font-bold uppercase ${s.border} ${s.bg} ${s.text}`}>
          {s.label}
        </span>
        <span className="font-mono text-[9px] text-muted">{relativeTime(item.created_at)}</span>
      </div>
    </Link>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [radarSummary, setRadarSummary]         = useState<RadarV2SummaryResponse | null>(null);
  const [coverageSummary, setCoverageSummary]   = useState<CoverageV2SummaryResponse | null>(null);
  const [recentSignals, setRecentSignals]       = useState<RadarV2SignalItem[]>([]);
  const [radarLoading, setRadarLoading]         = useState(true);
  const [coverageLoading, setCoverageLoading]   = useState(true);
  const [signalsLoading, setSignalsLoading]     = useState(true);
  const [lastUpdated, setLastUpdated]           = useState<string | null>(null);

  function loadAll() {
    setRadarLoading(true);
    setCoverageLoading(true);
    setSignalsLoading(true);

    getRadarV2Summary({})
      .then(setRadarSummary)
      .catch(() => setRadarSummary(null))
      .finally(() => setRadarLoading(false));

    getCoverageV2Summary()
      .then(setCoverageSummary)
      .catch(() => setCoverageSummary(null))
      .finally(() => setCoverageLoading(false));

    getRadarV2Signals({ limit: 8, sort: "analysis_date" })
      .then((r) => setRecentSignals(r.items))
      .catch(() => setRecentSignals([]))
      .finally(() => setSignalsLoading(false));

    setLastUpdated(new Date().toISOString());
  }

  useEffect(() => { loadAll(); }, []);

  const pipelineCfg = PIPELINE_CFG[coverageSummary?.pipeline.overall_status ?? "healthy"] ?? PIPELINE_CFG.healthy;
  const PipelineIcon = pipelineCfg.Icon;

  return (
    <div className="min-h-screen">

      {/* ── Page header ─────────────────────────────────────────── */}
      <div className="border-b border-border bg-surface-card">
        <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-accent-subtle border border-accent/20">
                <LayoutDashboard className="h-6 w-6 text-accent" />
              </div>
              <div>
                <h1 className="font-display text-2xl font-bold tracking-tight text-primary sm:text-3xl">Dashboard Operacional</h1>
                <p className="mt-1.5 text-sm text-secondary leading-relaxed">Visão consolidada do estado atual do sistema de inteligência investigativa</p>
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              {lastUpdated && (
                <div className="flex items-center gap-1.5 text-xs text-muted">
                  <Clock className="h-3.5 w-3.5" />
                  <span className="font-mono tabular-nums">
                    {new Date(lastUpdated).toLocaleTimeString("pt-BR")}
                  </span>
                </div>
              )}
              <button
                onClick={loadAll}
                disabled={radarLoading || coverageLoading || signalsLoading}
                className="flex items-center gap-1.5 rounded-lg border border-border bg-surface-card px-3 py-2 text-xs font-semibold text-secondary transition hover:text-primary hover:border-accent/30 disabled:opacity-50"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${radarLoading || coverageLoading ? "animate-spin" : ""}`} />
                Atualizar
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ── Body ────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6 space-y-8">

        {/* ── KPI row ──────────────────────────────────────────── */}
        <section>
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted mb-3">Métricas Gerais</p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-8">
            <KpiCard label="Total Sinais"  value={formatNumber(radarSummary?.totals.signals ?? 0)}  loading={radarLoading}    />
            <KpiCard label="Total Casos"   value={formatNumber(radarSummary?.totals.cases ?? 0)}   loading={radarLoading}    />
            <KpiCard label="Crítico"       value={radarSummary?.severity_counts.critical ?? 0}     dot="bg-error"     loading={radarLoading}    />
            <KpiCard label="Alto"          value={radarSummary?.severity_counts.high     ?? 0}     dot="bg-amber"      loading={radarLoading}    />
            <KpiCard label="Médio"         value={radarSummary?.severity_counts.medium   ?? 0}     dot="bg-yellow-500" loading={radarLoading}    />
            <KpiCard label="Baixo"         value={radarSummary?.severity_counts.low      ?? 0}     dot="bg-info"       loading={radarLoading}    />
            <KpiCard label="Fontes"        value={coverageSummary?.totals.connectors ?? 0}         loading={coverageLoading} sub={`${coverageSummary?.totals.jobs_enabled ?? 0} jobs ativos`} />
            <KpiCard label="Sinais (dados)"value={formatNumber(coverageSummary?.totals.signals_total ?? 0)} loading={coverageLoading} />
          </div>
        </section>

        {/* ── Status cards ─────────────────────────────────────── */}
        <section>
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted mb-3">Estado dos Sistemas</p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">

            {/* Radar status */}
            <div className="rounded-xl border border-border bg-surface-card p-5">
              <div className="flex items-start justify-between gap-2 mb-4">
                <div className="flex items-center gap-2">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent-subtle border border-accent/20">
                    <Radar className="h-4.5 w-4.5 text-accent" />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-primary">Radar de Riscos</p>
                    <p className="font-mono text-[10px] text-muted">/radar</p>
                  </div>
                </div>
              </div>
              <div className="space-y-2">
                {[
                  { label: "Críticos",  value: radarSummary?.severity_counts.critical ?? 0, dot: "bg-error" },
                  { label: "Altos",     value: radarSummary?.severity_counts.high     ?? 0, dot: "bg-amber" },
                  { label: "Médios",    value: radarSummary?.severity_counts.medium   ?? 0, dot: "bg-yellow-500" },
                  { label: "Baixos",    value: radarSummary?.severity_counts.low      ?? 0, dot: "bg-info" },
                ].map((row) => (
                  <div key={row.label} className="flex items-center justify-between text-xs">
                    <span className="flex items-center gap-1.5 text-secondary">
                      <span className={`h-1.5 w-1.5 rounded-full ${row.dot}`} />
                      {row.label}
                    </span>
                    <span className="font-mono font-bold text-primary tabular-nums">
                      {radarLoading ? "—" : formatNumber(row.value)}
                    </span>
                  </div>
                ))}
              </div>
              <Link
                href="/radar"
                className="mt-4 flex items-center gap-1.5 text-xs font-semibold text-accent hover:underline"
              >
                Abrir Radar <ArrowRight className="h-3 w-3" />
              </Link>
            </div>

            {/* Pipeline status */}
            <div className="rounded-xl border border-border bg-surface-card p-5">
              <div className="flex items-start justify-between gap-2 mb-4">
                <div className="flex items-center gap-2">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent-subtle border border-accent/20">
                    <Workflow className="h-4.5 w-4.5 text-accent" />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-primary">Pipeline de Dados</p>
                    <p className="font-mono text-[10px] text-muted">/coverage</p>
                  </div>
                </div>
                {!coverageLoading && coverageSummary && (
                  <span className={`flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase ${pipelineCfg.cls}`}>
                    <PipelineIcon className="h-3 w-3" />
                    {pipelineCfg.label}
                  </span>
                )}
              </div>
              <div className="space-y-2">
                {[
                  { label: "Fontes ativas",  value: coverageSummary?.totals.connectors ?? 0 },
                  { label: "Jobs ativos",    value: coverageSummary?.totals.jobs_enabled ?? 0, total: coverageSummary?.totals.jobs },
                  { label: "Fontes com erro",value: coverageSummary?.totals.status_counts.error ?? 0 },
                  { label: "Travados",       value: coverageSummary?.totals.runtime.failed_or_stuck ?? 0 },
                ].map((row) => (
                  <div key={row.label} className="flex items-center justify-between text-xs">
                    <span className="text-secondary">{row.label}</span>
                    <span className="font-mono font-bold text-primary tabular-nums">
                      {coverageLoading ? "—" : row.total != null ? `${row.value}/${row.total}` : row.value}
                    </span>
                  </div>
                ))}
              </div>
              <Link
                href="/coverage"
                className="mt-4 flex items-center gap-1.5 text-xs font-semibold text-accent hover:underline"
              >
                Ver Cobertura <ArrowRight className="h-3 w-3" />
              </Link>
            </div>

            {/* Quick links */}
            <div className="rounded-xl border border-border bg-surface-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent-subtle border border-accent/20">
                  <TrendingUp className="h-4.5 w-4.5 text-accent" />
                </div>
                <div>
                  <p className="text-sm font-bold text-primary">Acesso Rápido</p>
                  <p className="font-mono text-[10px] text-muted">atalhos</p>
                </div>
              </div>
              <div className="space-y-1.5">
                {[
                  { href: "/radar?severity=critical", label: "Sinais Críticos", icon: AlertTriangle, cls: "text-error" },
                  { href: "/radar?view=cases",        label: "Casos Ativos",    icon: FileText,      cls: "text-amber" },
                  { href: "/coverage",                label: "Cobertura",       icon: Database,      cls: "text-accent" },
                  { href: "/methodology",             label: "Metodologia",     icon: ShieldCheck,   cls: "text-muted"  },
                  { href: "/api-health",              label: "Saúde da API",    icon: Activity,      cls: "text-muted"  },
                ].map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-medium text-secondary transition hover:bg-surface-subtle hover:text-primary"
                  >
                    <item.icon className={`h-3.5 w-3.5 shrink-0 ${item.cls}`} />
                    {item.label}
                    <ArrowRight className="ml-auto h-3 w-3 text-muted opacity-0 transition group-hover:opacity-100 group-hover:translate-x-0.5" />
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ── Recent signals ────────────────────────────────────── */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-widest text-muted">Sinais Recentes</p>
              <p className="text-sm font-semibold text-primary mt-0.5">Últimos sinais detectados pelo pipeline</p>
            </div>
            <Link
              href="/radar"
              className="flex items-center gap-1 text-xs font-semibold text-accent hover:underline"
            >
              Ver todos
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="rounded-xl border border-border bg-surface-card overflow-hidden">
            {signalsLoading ? (
              <div className="divide-y divide-border">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-3 px-3 py-3">
                    <div className="h-2 w-2 rounded-full bg-surface-subtle animate-pulse shrink-0" />
                    <div className="flex-1 space-y-1.5">
                      <div className="h-3 w-3/4 rounded bg-surface-subtle animate-pulse" />
                      <div className="h-2.5 w-1/2 rounded bg-surface-subtle animate-pulse" />
                    </div>
                  </div>
                ))}
              </div>
            ) : recentSignals.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 gap-2">
                <Radar className="h-7 w-7 text-muted" />
                <p className="text-sm text-muted">Nenhum sinal disponível no momento.</p>
                <p className="text-xs text-muted/70">Aguarde a próxima execução do pipeline de detecção.</p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {recentSignals.map((item) => (
                  <SignalRow key={item.id} item={item} />
                ))}
              </div>
            )}
          </div>
        </section>

        {/* ── Pipeline stages preview ───────────────────────────── */}
        {!coverageLoading && coverageSummary && (
          <section>
            <p className="font-mono text-[10px] uppercase tracking-widest text-muted mb-3">Etapas do Pipeline</p>
            <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${coverageSummary.pipeline.stages.length}, minmax(0, 1fr))` }}>
              {coverageSummary.pipeline.stages.map((stage) => {
                const statusMap: Record<string, { dot: string; text: string; bg: string; border: string; label: string }> = {
                  up_to_date: { dot: "bg-success",    text: "text-success",    bg: "bg-success/5",    border: "border-success/20",    label: "Atualizado"    },
                  stale:      { dot: "bg-amber",      text: "text-amber",      bg: "bg-amber/5",      border: "border-amber/20",      label: "Desatualizado" },
                  processing: { dot: "bg-accent",     text: "text-accent",     bg: "bg-accent/5",     border: "border-accent/20",     label: "Processando"   },
                  warning:    { dot: "bg-amber",      text: "text-amber",      bg: "bg-amber/5",      border: "border-amber/20",      label: "Atenção"       },
                  error:      { dot: "bg-error",      text: "text-error",      bg: "bg-error/5",      border: "border-error/20",      label: "Erro"          },
                  pending:    { dot: "bg-muted/50",   text: "text-muted",      bg: "bg-surface-base", border: "border-border",        label: "Pendente"      },
                };
                const scfg = statusMap[stage.status] ?? statusMap.pending;
                return (
                  <div key={stage.code} className={`rounded-xl border ${scfg.border} ${scfg.bg} p-3 text-center`}>
                    <div className={`flex items-center justify-center gap-1.5 mb-1`}>
                      <span className={`h-2 w-2 rounded-full ${scfg.dot}`} />
                      <p className={`font-mono text-[9px] font-bold uppercase tracking-wide ${scfg.text}`}>{scfg.label}</p>
                    </div>
                    <p className="text-xs font-semibold text-primary leading-snug">{stage.label}</p>
                    {stage.reason && stage.status !== "up_to_date" && (
                      <p className="text-[10px] text-muted mt-1 leading-snug">{stage.reason}</p>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* ── Snapshot footer ──────────────────────────────────── */}
        {coverageSummary?.snapshot_at && (
          <div className="flex items-center gap-1.5 text-[11px] text-muted">
            <Calendar className="h-3 w-3" />
            Snapshot dos dados: <span className="font-mono">{new Date(coverageSummary.snapshot_at).toLocaleString("pt-BR")}</span>
          </div>
        )}
      </div>
    </div>
  );
}
