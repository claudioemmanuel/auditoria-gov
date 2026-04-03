"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  getCoverageV2Analytics,
  getCoverageV2SourcePreview,
  getCoverageV2Sources,
  getCoverageV2Summary,
} from "@/lib/api";
import {
  getPipelineCapacity,
  getPipelineStatus,
  triggerFullPipeline,
  type PipelineCapacity,
  type PipelineDispatchResponse,
  type PipelineStatusResponse,
} from "@/lib/operatorApiClient";
import type {
  AnalyticalCoverageItem,
  CoverageStatus,
  CoverageV2AnalyticsResponse,
  CoverageV2LatestRun,
  CoverageV2SourceItem,
  CoverageV2SourcePreviewResponse,
  CoverageV2SummaryResponse,
} from "@/lib/types";
import { formatNumber } from "@/lib/utils";
import { Button } from "@/components/Button";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  Database,
  FileText,
  Lightbulb,
  BookOpen,
  Loader2,
  Package,
  Play,
  RefreshCw,
  Search,
  X,
  XCircle,
  Zap,
} from "lucide-react";

// ── Status config ─────────────────────────────────────────────────────────────

const STATUS_CFG: Record<CoverageStatus, {
  label: string;
  dotColor: string;
  textColor: string;
  borderColor: string;
  bgColor: string;
  badge: string;
}> = {
  ok:      { label: "OK",       dotColor: "var(--color-low)",      textColor: "var(--color-low-text)",      borderColor: "var(--color-low-border)",      bgColor: "var(--color-low-bg)",      badge: "ow-badge ow-badge-low"      },
  warning: { label: "Atenção",  dotColor: "var(--color-medium)",   textColor: "var(--color-medium-text)",   borderColor: "var(--color-medium-border)",   bgColor: "var(--color-medium-bg)",   badge: "ow-badge ow-badge-medium"   },
  stale:   { label: "Defasado", dotColor: "var(--color-high)",     textColor: "var(--color-high-text)",     borderColor: "var(--color-high-border)",     bgColor: "var(--color-high-bg)",     badge: "ow-badge ow-badge-high"     },
  error:   { label: "Erro",     dotColor: "var(--color-critical)", textColor: "var(--color-critical-text)", borderColor: "var(--color-critical-border)", bgColor: "var(--color-critical-bg)", badge: "ow-badge ow-badge-critical"  },
  pending: { label: "Pendente", dotColor: "var(--color-text-3)",   textColor: "var(--color-text-3)",        borderColor: "var(--color-border)",          bgColor: "transparent",              badge: "ow-badge ow-badge-neutral"  },
};

const RUN_STATUS_CFG: Record<string, { dotColor: string; textColor: string; label: string }> = {
  completed: { dotColor: "var(--color-low)",      textColor: "var(--color-low-text)",      label: "Concluído"  },
  running:   { dotColor: "var(--color-amber)",     textColor: "var(--color-amber-text)",    label: "Executando" },
  error:     { dotColor: "var(--color-critical)",  textColor: "var(--color-critical-text)", label: "Erro"       },
  failed:    { dotColor: "var(--color-critical)",  textColor: "var(--color-critical-text)", label: "Falhou"     },
  yielded:   { dotColor: "var(--color-medium)",    textColor: "var(--color-medium-text)",   label: "Cedeu vez"  },
  stuck:     { dotColor: "var(--color-high)",      textColor: "var(--color-high-text)",     label: "Travado"    },
  skipped:   { dotColor: "var(--color-text-3)",    textColor: "var(--color-text-3)",        label: "Ignorado"   },
  pending:   { dotColor: "var(--color-text-3)",    textColor: "var(--color-text-3)",        label: "Pendente"   },
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatLag(hours: number | null | undefined): string {
  if (hours == null) return "—";
  if (hours < 1) return "<1h";
  if (hours < 24) return `${Math.round(hours)}h`;
  if (hours < 24 * 30) return `${Math.round(hours / 24)}d`;
  return `${Math.round(hours / 24 / 30)}m`;
}

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

function formatDuration(start: string | null | undefined, end: string | null | undefined): string {
  if (!start || !end) return "—";
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (ms < 60000) return `${Math.round(ms / 1000)}s`;
  if (ms < 3600000) return `${Math.round(ms / 60000)}min`;
  return `${(ms / 3600000).toFixed(1)}h`;
}

function fmtDate(d: string | null | undefined): string {
  if (!d) return "—";
  return new Date(d).toLocaleString("pt-BR", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function lagColor(hours: number | null | undefined): string {
  if (hours == null) return "var(--color-text-3)";
  if (hours > 48) return "var(--color-critical-text)";
  if (hours > 24) return "var(--color-high-text)";
  return "var(--color-low-text)";
}

// ── Coverage status badge ─────────────────────────────────────────────────────

function CoverageStatusBadge({ status }: { status: CoverageStatus }) {
  const cfg = STATUS_CFG[status] ?? STATUS_CFG.pending;
  return (
    <span className={cfg.badge}>
      <span className="inline-block h-1.5 w-1.5 rounded-full mr-1" style={{ background: cfg.dotColor }} />
      {cfg.label}
    </span>
  );
}

// ── Run card ──────────────────────────────────────────────────────────────────

function RunCard({ run }: { run: CoverageV2LatestRun }) {
  const key = run.is_stuck ? "stuck" : run.status;
  const cfg = RUN_STATUS_CFG[key] ?? RUN_STATUS_CFG.pending;

  return (
    <div className="ow-card p-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full shrink-0" style={{ background: cfg.dotColor }} />
          <span className="text-mono-xs font-bold" style={{ color: cfg.textColor }}>
            {run.is_stuck ? "Travado" : (RUN_STATUS_CFG[run.status]?.label ?? run.status)}
          </span>
          <span className="text-mono-xs" style={{ color: "var(--color-text-3)" }}>
            {formatDuration(run.started_at, run.finished_at)}
          </span>
        </div>
        <Link
          href={`/coverage/run/${run.id}`}
          className="flex items-center gap-1 text-mono-xs hover:underline"
          style={{ color: "var(--color-amber-text)" }}
        >
          Detalhar
          <ArrowUpRight className="h-2.5 w-2.5" />
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <p className="text-mono-xs uppercase tracking-wide mb-0.5" style={{ color: "var(--color-text-3)" }}>Início</p>
          <p className="text-mono-xs" style={{ color: "var(--color-text)" }}>{fmtDate(run.started_at)}</p>
        </div>
        <div>
          <p className="text-mono-xs uppercase tracking-wide mb-0.5" style={{ color: "var(--color-text-3)" }}>Fim</p>
          <p className="text-mono-xs" style={{ color: "var(--color-text)" }}>{fmtDate(run.finished_at)}</p>
        </div>
      </div>

      {(run.items_fetched > 0 || run.items_normalized > 0) && (
        <div className="flex items-center gap-4 text-caption">
          <span className="flex items-center gap-1" style={{ color: "var(--color-text-3)" }}>
            <Package className="h-3 w-3 shrink-0" />
            <span className="text-mono-xs font-bold" style={{ color: "var(--color-text)" }}>
              {run.items_fetched.toLocaleString("pt-BR")}
            </span>
            <span>coletados</span>
          </span>
          <span className="flex items-center gap-1" style={{ color: "var(--color-text-3)" }}>
            <CheckCircle2 className="h-3 w-3 shrink-0" style={{ color: "var(--color-low-text)" }} />
            <span className="text-mono-xs font-bold" style={{ color: "var(--color-text)" }}>
              {run.items_normalized.toLocaleString("pt-BR")}
            </span>
            <span>normalizados</span>
          </span>
        </div>
      )}

      {run.status === "running" && (
        <div className="space-y-1.5 mt-2">
          <div className="flex items-center gap-2">
            <div className="ow-score-bar-track flex-1">
              <div className="ow-score-bar-fill animate-pulse" style={{ width: "100%", background: "var(--color-amber)" }} />
            </div>
            <span className="text-mono-xs font-bold" style={{ color: "var(--color-amber-text)" }}>Coletando</span>
          </div>
          <div className="flex items-center gap-3 text-mono-xs" style={{ color: "var(--color-text-3)" }}>
            {run.cursor_info && <span style={{ color: "var(--color-text)" }}>{run.cursor_info}</span>}
            {run.rate_per_min != null && run.rate_per_min > 0 && (
              <span>~{Math.round(run.rate_per_min).toLocaleString("pt-BR")}/min</span>
            )}
            {run.pages_fetched != null && run.pages_fetched > 0 && (
              <span>{run.pages_fetched.toLocaleString("pt-BR")} pags</span>
            )}
          </div>
          {run.elapsed_seconds != null && (
            <p className="text-mono-xs" style={{ color: "var(--color-text-3)" }}>
              Tempo decorrido: {formatElapsed(run.elapsed_seconds)}
            </p>
          )}
        </div>
      )}

      {run.status === "yielded" && run.items_fetched > 0 && run.items_normalized < run.items_fetched && (
        <div className="space-y-1 mt-2">
          <div className="flex items-center gap-2">
            <div className="ow-score-bar-track flex-1">
              <div
                className="ow-score-bar-fill transition-all duration-500"
                style={{
                  width: `${Math.min((run.items_normalized / run.items_fetched) * 100, 100)}%`,
                  background: "var(--color-low)",
                }}
              />
            </div>
            <span className="text-mono-xs font-bold" style={{ color: "var(--color-low-text)" }}>
              {Math.round((run.items_normalized / run.items_fetched) * 100)}% normalizado
            </span>
          </div>
        </div>
      )}

      {run.error_message && (
        <div className="ow-alert ow-alert-error">
          <AlertTriangle className="h-3 w-3 shrink-0" />
          <p className="text-mono-xs">{run.error_message}</p>
        </div>
      )}
    </div>
  );
}

// ── KPI Strip ─────────────────────────────────────────────────────────────────

function KpiStrip({ summary, loading }: { summary: CoverageV2SummaryResponse | null; loading: boolean }) {
  if (loading) {
    return (
      <div className="ow-strip">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="ow-strip-item">
            <div className="ow-skeleton h-6 w-12 rounded mb-1" />
            <div className="ow-skeleton h-3 w-16 rounded" />
          </div>
        ))}
      </div>
    );
  }

  const t = summary?.totals;
  const sc = t?.status_counts;
  const rt = t?.runtime;

  const kpis: { label: string; value: number | string; sub?: string; dotColor?: string }[] = [
    { label: "Fontes",   value: t?.connectors ?? 0 },
    { label: "Jobs",     value: t?.jobs ?? 0,         sub: `${t?.jobs_enabled ?? 0} ativos` },
    { label: "Sinais",   value: formatNumber(t?.signals_total ?? 0) },
    { label: "OK",       value: sc?.ok ?? 0,           dotColor: "var(--color-low)"      },
    { label: "Atenção",  value: sc?.warning ?? 0,      dotColor: "var(--color-medium)"   },
    { label: "Defasado", value: sc?.stale ?? 0,        dotColor: "var(--color-high)"     },
    { label: "Erro",     value: sc?.error ?? 0,        dotColor: "var(--color-critical)" },
    { label: "Travados", value: rt?.failed_or_stuck ?? 0, dotColor: rt?.failed_or_stuck ? "var(--color-critical)" : "var(--color-text-3)" },
  ];

  return (
    <div className="ow-strip">
      {kpis.map((k) => (
        <div key={k.label} className="ow-strip-item">
          <div className="flex items-center gap-1.5">
            {k.dotColor && (
              <span className="h-1.5 w-1.5 rounded-full shrink-0" style={{ background: k.dotColor }} />
            )}
            <span className="ow-strip-value text-mono">{k.value}</span>
          </div>
          <span className="ow-strip-label">{k.label}</span>
          {k.sub && (
            <span className="text-mono-xs" style={{ color: "var(--color-text-3)" }}>{k.sub}</span>
          )}
        </div>
      ))}
    </div>
  );
}

// ── Pipeline stage strip ──────────────────────────────────────────────────────

const STAGE_STATUS: Record<string, {
  label: string;
  icon: React.ReactNode;
  ringColor: string;
  bgColor: string;
  textColor: string;
}> = {
  up_to_date: { label: "Atualizado",    icon: <CheckCircle2 className="h-5 w-5" />, ringColor: "var(--color-low-border)",      bgColor: "var(--color-low-bg)",      textColor: "var(--color-low-text)"      },
  stale:      { label: "Desatualizado", icon: <Clock className="h-5 w-5" />,        ringColor: "var(--color-high-border)",     bgColor: "var(--color-high-bg)",     textColor: "var(--color-high-text)"     },
  processing: { label: "Processando",   icon: <Activity className="h-5 w-5" />,     ringColor: "var(--color-amber-border)",    bgColor: "var(--color-amber-dim)",   textColor: "var(--color-amber-text)"    },
  warning:    { label: "Atenção",       icon: <AlertTriangle className="h-5 w-5" />, ringColor: "var(--color-medium-border)",  bgColor: "var(--color-medium-bg)",   textColor: "var(--color-medium-text)"   },
  error:      { label: "Erro",          icon: <XCircle className="h-5 w-5" />,       ringColor: "var(--color-critical-border)",bgColor: "var(--color-critical-bg)", textColor: "var(--color-critical-text)" },
  pending:    { label: "Pendente",      icon: <Clock className="h-5 w-5" />,         ringColor: "var(--color-border)",         bgColor: "var(--color-surface-3)",   textColor: "var(--color-text-3)"        },
};

function PipelineStrip({ summary }: { summary: CoverageV2SummaryResponse | null }) {
  if (!summary) return null;
  const stages = summary.pipeline.stages;
  const overallStatus = summary.pipeline.overall_status;

  const overallColor =
    overallStatus === "healthy" ? "var(--color-low-text)" :
    overallStatus === "attention" ? "var(--color-amber-text)" :
    "var(--color-critical-text)";
  const overallBadge =
    overallStatus === "healthy" ? "ow-badge ow-badge-low" :
    overallStatus === "attention" ? "ow-badge ow-badge-amber" :
    "ow-badge ow-badge-critical";
  const overallLabel =
    overallStatus === "healthy" ? "Saudável" :
    overallStatus === "attention" ? "Atenção" :
    "Bloqueado";

  return (
    <div className="ow-card p-5">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2.5">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-lg"
            style={{ background: "var(--color-surface-3)" }}
          >
            <Zap className="h-4 w-4" style={{ color: "var(--color-text-3)" }} />
          </div>
          <p className="text-mono-xs uppercase tracking-widest" style={{ color: "var(--color-text-3)" }}>
            Pipeline de Ingestão
          </p>
        </div>
        <span className={overallBadge}>{overallLabel}</span>
      </div>

      <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${stages.length}, minmax(0, 1fr))` }}>
        {stages.map((stage, i) => {
          const scfg = STAGE_STATUS[stage.status] ?? STAGE_STATUS.pending;
          const isProcessing = stage.status === "processing";
          return (
            <div key={stage.code} className="relative">
              {i < stages.length - 1 && (
                <div
                  className="absolute top-6 left-[calc(50%+1.5rem)] right-[-calc(50%-1.5rem)] h-px z-0"
                  style={{ background: "var(--color-border)" }}
                />
              )}
              <div
                className="relative z-10 rounded-xl border-2 p-4 flex flex-col items-center gap-3 text-center overflow-hidden"
                style={{ borderColor: scfg.ringColor, background: scfg.bgColor }}
              >
                {isProcessing && (
                  <div
                    className="absolute inset-x-0 top-0 h-0.5 animate-[slide_2s_linear_infinite]"
                    style={{ background: `linear-gradient(to right, transparent, var(--color-amber), transparent)` }}
                  />
                )}
                <div
                  className="flex h-12 w-12 items-center justify-center rounded-full shadow-sm"
                  style={{ background: "var(--color-surface)", color: scfg.textColor }}
                >
                  {scfg.icon}
                </div>
                <div>
                  <p className="text-label font-bold leading-snug" style={{ color: "var(--color-text)" }}>
                    {stage.label}
                  </p>
                  <p className="text-mono-xs font-bold uppercase mt-0.5" style={{ color: scfg.textColor }}>
                    {scfg.label}
                  </p>
                  {stage.reason && stage.status !== "up_to_date" && (
                    <p className="text-caption mt-1.5 leading-snug" style={{ color: "var(--color-text-2)" }}>
                      {stage.reason}
                    </p>
                  )}
                </div>
                {isProcessing && (
                  <div className="ow-score-bar-track w-full">
                    <div
                      className="ow-score-bar-fill animate-[progress_1.5s_ease-in-out_infinite]"
                      style={{ width: "33%", background: "var(--color-amber)" }}
                    />
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Effective badge (running overrides status) ────────────────────────────────

function EffectiveBadge({ item }: { item: CoverageV2SourceItem }) {
  if (item.runtime.running_jobs > 0) {
    return (
      <span className="ow-badge ow-badge-amber">
        <span className="inline-block h-1.5 w-1.5 rounded-full mr-1 animate-pulse" style={{ background: "var(--color-amber)" }} />
        Executando
      </span>
    );
  }
  return <CoverageStatusBadge status={item.worst_status} />;
}

// ── Source diagnostic modal ───────────────────────────────────────────────────

function SourceDiagnosticModal({
  item,
  preview,
  loading,
  error,
  onClose,
}: {
  item: CoverageV2SourceItem;
  preview: CoverageV2SourcePreviewResponse | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
}) {
  const cfg = STATUS_CFG[item.worst_status] ?? STATUS_CFG.pending;

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 backdrop-blur-sm"
        style={{ background: "rgba(0,0,0,0.7)" }}
        onClick={onClose}
        aria-hidden="true"
      />

      <div
        className="relative z-10 flex w-full max-w-3xl max-h-[88vh] flex-col rounded-2xl border shadow-2xl overflow-hidden"
        style={{ background: "var(--color-surface)", borderColor: "var(--color-border-strong)" }}
      >
        {/* Header */}
        <div
          className="flex items-start justify-between gap-4 border-b px-6 py-4"
          style={{ borderColor: "var(--color-border)", background: cfg.bgColor }}
        >
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-display-sm font-bold capitalize" style={{ color: "var(--color-text)" }}>
                {item.connector_label}
              </h2>
              <EffectiveBadge item={item} />
            </div>
            <p className="text-mono-xs mt-0.5" style={{ color: "var(--color-text-3)" }}>{item.connector}</p>
          </div>
          <button
            onClick={onClose}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border transition-colors"
            style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)", color: "var(--color-text-3)" }}
            aria-label="Fechar diagnóstico"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Summary strip */}
        <div
          className="grid grid-cols-4 gap-3 border-b px-6 py-4"
          style={{ borderColor: "var(--color-border)" }}
        >
          {[
            { label: "Jobs",        value: item.job_count,             sub: `${item.enabled_job_count} habilitados`, color: undefined },
            { label: "Em execução", value: item.runtime.running_jobs,  sub: null,                                    color: item.runtime.running_jobs > 0 ? "var(--color-amber-text)" : undefined },
            { label: "Com erro",    value: item.runtime.error_jobs,    sub: null,                                    color: item.runtime.error_jobs > 0 ? "var(--color-critical-text)" : undefined },
            {
              label: "Defasagem",
              value: formatLag(item.max_freshness_lag_hours),
              sub: item.last_success_at ? new Date(item.last_success_at).toLocaleString("pt-BR") : null,
              color: lagColor(item.max_freshness_lag_hours),
            },
          ].map((m) => (
            <div key={m.label}>
              <p className="text-mono-xs uppercase tracking-widest mb-1" style={{ color: "var(--color-text-3)" }}>{m.label}</p>
              <p className="text-mono font-bold leading-none" style={{ color: m.color ?? "var(--color-text)" }}>{m.value}</p>
              {m.sub && <p className="text-mono-xs mt-0.5" style={{ color: "var(--color-text-3)" }}>{m.sub}</p>}
            </div>
          ))}
        </div>

        {/* Body */}
        <div
          className="flex-1 overflow-y-auto px-6 py-5 space-y-6"
          style={{ background: "var(--color-surface-2)" }}
        >
          {loading && (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="ow-skeleton h-20 rounded-xl" />
              ))}
            </div>
          )}

          {error && (
            <div className="ow-alert ow-alert-error">
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
              {error}
            </div>
          )}

          {preview && (
            <>
              {item.runtime.stuck_jobs > 0 && (
                <div className="ow-alert ow-alert-error">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  {item.runtime.stuck_jobs} job(s) travado(s) — restart recomendado
                </div>
              )}

              {preview.insights.length > 0 && (
                <section>
                  <p className="text-mono-xs uppercase tracking-widest mb-3" style={{ color: "var(--color-text-3)" }}>
                    Insights ({preview.insights.length})
                  </p>
                  <div className="space-y-2">
                    {preview.insights.map((insight, i) => (
                      <div key={i} className="ow-alert ow-alert-info">
                        <Lightbulb className="h-4 w-4 shrink-0 mt-0.5" />
                        <p className="text-body leading-relaxed">{insight}</p>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              <section>
                <p className="text-mono-xs uppercase tracking-widest mb-3" style={{ color: "var(--color-text-3)" }}>
                  Jobs ({preview.jobs.length})
                </p>
                <div className="space-y-4">
                  {[...preview.jobs].sort((a, b) => {
                    const aRun = a.latest_run?.status === "running" ? 0 : 1;
                    const bRun = b.latest_run?.status === "running" ? 0 : 1;
                    if (aRun !== bRun) return aRun - bRun;
                    const order = ["error", "warning", "stale", "ok", "pending"];
                    return order.indexOf(a.status) - order.indexOf(b.status);
                  }).map((job) => {
                    const isJobRunning = job.latest_run?.status === "running";
                    const scfg = STATUS_CFG[job.status] ?? STATUS_CFG.pending;
                    return (
                      <div
                        key={job.job}
                        className="rounded-xl border p-4 space-y-4"
                        style={{
                          borderColor: isJobRunning ? "var(--color-amber-border)" : scfg.borderColor,
                          background: isJobRunning ? "var(--color-amber-dim)" : "var(--color-surface)",
                        }}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="flex items-center gap-2 flex-wrap mb-1">
                              <span className="text-mono font-bold" style={{ color: "var(--color-text)" }}>{job.job}</span>
                              {!job.enabled_in_mvp && (
                                <span className="ow-badge ow-badge-neutral text-mono-xs">Desabilitado</span>
                              )}
                            </div>
                            <p className="text-mono-xs" style={{ color: "var(--color-amber-text)" }}>{job.domain}</p>
                            {job.description && (
                              <p className="text-caption mt-1 leading-relaxed" style={{ color: "var(--color-text-2)" }}>
                                {job.description}
                              </p>
                            )}
                          </div>
                          {isJobRunning ? (
                            <span className="ow-badge ow-badge-amber">
                              <span className="inline-block h-1.5 w-1.5 rounded-full mr-1 animate-pulse" style={{ background: "var(--color-amber)" }} />
                              Executando
                            </span>
                          ) : (
                            <CoverageStatusBadge status={job.status} />
                          )}
                        </div>

                        <div className="grid grid-cols-3 gap-3">
                          {[
                            {
                              label: isJobRunning ? "Coletados até agora" : "Itens coletados",
                              value: job.total_items.toLocaleString("pt-BR"),
                              sub: isJobRunning && job.latest_run?.cursor_info ? job.latest_run.cursor_info : null,
                              color: "var(--color-text)",
                            },
                            {
                              label: "Defasagem",
                              value: formatLag(job.freshness_lag_hours),
                              sub: null,
                              color: lagColor(job.freshness_lag_hours),
                            },
                            {
                              label: "Último sucesso",
                              value: job.last_success_at ? fmtDate(job.last_success_at) : "Não registrado",
                              sub: null,
                              color: "var(--color-text)",
                            },
                          ].map((m) => (
                            <div
                              key={m.label}
                              className="rounded-lg border px-3 py-2"
                              style={{ borderColor: "var(--color-border)", background: "var(--color-surface-2)" }}
                            >
                              <p className="text-mono-xs uppercase tracking-wide mb-0.5" style={{ color: "var(--color-text-3)" }}>
                                {m.label}
                              </p>
                              <p className="text-mono-xs font-bold" style={{ color: m.color }}>
                                {m.value}
                              </p>
                              {m.sub && (
                                <p className="text-mono-xs mt-0.5" style={{ color: "var(--color-amber-text)" }}>{m.sub}</p>
                              )}
                            </div>
                          ))}
                        </div>

                        {job.latest_run && <JobPipelineStrip run={job.latest_run} />}
                        {job.latest_run && (
                          <div>
                            <p className="text-mono-xs uppercase tracking-wide mb-2" style={{ color: "var(--color-text-3)" }}>
                              Execução mais recente
                            </p>
                            <RunCard run={job.latest_run} />
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </section>
            </>
          )}
        </div>

        {/* Footer */}
        <div
          className="flex items-center justify-between border-t px-6 py-3"
          style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}
        >
          <p className="text-mono-xs" style={{ color: "var(--color-text-3)" }}>
            Último sucesso:{" "}
            <span style={{ color: "var(--color-text)" }}>
              {item.last_success_at ? new Date(item.last_success_at).toLocaleString("pt-BR") : "—"}
            </span>
          </p>
          <Button variant="ghost" size="sm" onClick={onClose}>Fechar</Button>
        </div>
      </div>
    </div>
  );
}

// ── Job pipeline strip ────────────────────────────────────────────────────────

function JobPipelineStrip({ run }: { run: CoverageV2LatestRun }) {
  const [nowMs, setNowMs] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNowMs(Date.now()), 10_000);
    return () => clearInterval(id);
  }, []);

  const isRunning = run.status === "running";
  const startMs = run.started_at ? new Date(run.started_at).getTime() : 0;
  const elapsedMs = startMs > 0 ? nowMs - startMs : 0;
  const elapsedMin = Math.floor(elapsedMs / 60_000);
  const elapsedSec = Math.floor((elapsedMs % 60_000) / 1_000);
  const elapsedStr =
    elapsedMin >= 60
      ? `${Math.floor(elapsedMin / 60)}h ${elapsedMin % 60}min`
      : elapsedMin > 0
      ? `${elapsedMin}min ${elapsedSec}s`
      : `${elapsedSec}s`;

  const ratePerMin =
    elapsedMs > 30_000 && run.items_fetched > 0
      ? Math.round(run.items_fetched / (elapsedMs / 60_000))
      : 0;

  const normPct =
    run.items_fetched > 0
      ? Math.min(100, Math.round((run.items_normalized / run.items_fetched) * 100))
      : 0;

  const isError = run.status === "error";
  const ingestDone = !isRunning && !isError;

  type StageStatus = "active" | "done" | "pending" | "error" | "blocked";
  const stages: { key: string; label: string; status: StageStatus; line1: string | null; line2: string | null }[] = [
    {
      key: "ingest",
      label: "Ingestão",
      status: isRunning ? "active" : isError ? "error" : "done",
      line1:
        isError
          ? "Erro na ingestão"
          : run.items_fetched > 0
          ? `${run.items_fetched.toLocaleString("pt-BR")} coletados`
          : isRunning
          ? "Iniciando…"
          : "0 itens",
      line2:
        isError && run.error_message
          ? run.error_message.length > 80
            ? run.error_message.slice(0, 77) + "…"
            : run.error_message
          : isRunning && ratePerMin > 0
          ? `~${ratePerMin}/min · ${elapsedStr}`
          : isRunning
          ? elapsedStr
          : null,
    },
    {
      key: "normalize",
      label: "Normalização",
      status: isError ? "blocked" : normPct >= 100 ? "done" : ingestDone ? "active" : "pending",
      line1:
        isError
          ? "Bloqueado por erro"
          : run.items_normalized > 0
          ? `${run.items_normalized.toLocaleString("pt-BR")} (${normPct}%)`
          : ingestDone
          ? "Processando…"
          : "Aguardando ingestão",
      line2: null,
    },
  ];

  function stageBorderColor(s: StageStatus) {
    if (s === "error") return "var(--color-critical-border)";
    if (s === "active") return "var(--color-amber-border)";
    if (s === "done") return "var(--color-low-border)";
    return "var(--color-border)";
  }
  function stageBgColor(s: StageStatus) {
    if (s === "error") return "var(--color-critical-bg)";
    if (s === "blocked") return "var(--color-surface-3)";
    if (s === "active") return "var(--color-amber-dim)";
    if (s === "done") return "var(--color-low-bg)";
    return "var(--color-surface-3)";
  }
  function stageTextColor(s: StageStatus) {
    if (s === "error") return "var(--color-critical-text)";
    if (s === "active") return "var(--color-amber-text)";
    if (s === "done") return "var(--color-low-text)";
    return "var(--color-text-3)";
  }
  function stageDotColor(s: StageStatus) {
    if (s === "error") return "var(--color-critical)";
    if (s === "active") return "var(--color-amber)";
    if (s === "done") return "var(--color-low)";
    return "var(--color-text-3)";
  }

  return (
    <div
      className="rounded-lg border px-3 py-2.5 space-y-2"
      style={{ borderColor: "var(--color-border)", background: "var(--color-surface-2)" }}
    >
      <div className="flex items-center justify-between">
        <p className="text-mono-xs uppercase tracking-widest" style={{ color: "var(--color-text-3)" }}>
          Pipeline de Processamento
        </p>
        {isRunning && startMs > 0 && (
          <span className="text-mono-xs" style={{ color: "var(--color-amber-text)" }}>{elapsedStr} em execução</span>
        )}
      </div>
      <div className="flex items-stretch gap-0.5">
        {stages.map((stage) => (
          <div
            key={stage.key}
            className="flex-1 rounded border px-2 py-1.5 min-w-0"
            style={{
              borderColor: stageBorderColor(stage.status),
              background: stageBgColor(stage.status),
              opacity: stage.status === "blocked" ? 0.5 : 1,
            }}
          >
            <div className="flex items-center gap-1 mb-0.5">
              <span className="h-1.5 w-1.5 rounded-full shrink-0" style={{ background: stageDotColor(stage.status) }} />
              <p className="text-mono-xs font-bold uppercase truncate" style={{ color: stageTextColor(stage.status) }}>
                {stage.label}
              </p>
            </div>
            {stage.line1 && (
              <p className="text-mono-xs leading-tight truncate" style={{ color: stageTextColor(stage.status), opacity: 0.8 }}>
                {stage.line1}
              </p>
            )}
            {stage.line2 && (
              <p className="text-mono-xs leading-tight" style={{ color: "var(--color-text-3)" }}>{stage.line2}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Source card ───────────────────────────────────────────────────────────────

function SourceCard({ item }: { item: CoverageV2SourceItem }) {
  const cfg = STATUS_CFG[item.worst_status] ?? STATUS_CFG.pending;
  const totalJobs = Object.values(item.status_counts).reduce((a, b) => a + b, 0);

  const [modalOpen, setModalOpen] = useState(false);
  const [preview, setPreview] = useState<CoverageV2SourcePreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  function fetchPreview(silent = false) {
    if (!silent) {
      setPreviewLoading(true);
      setPreviewError(null);
    }
    getCoverageV2SourcePreview(item.connector, { runs_limit: 5 })
      .then(setPreview)
      .catch(() => { if (!silent) setPreviewError("Não foi possível carregar o diagnóstico."); })
      .finally(() => { if (!silent) setPreviewLoading(false); });
  }

  function handleOpenModal() {
    setModalOpen(true);
    if (preview === null && !previewLoading) {
      fetchPreview();
    }
  }

  useEffect(() => {
    if (!modalOpen || item.runtime.running_jobs === 0) return;
    const interval = setInterval(() => fetchPreview(true), 5_000);
    return () => clearInterval(interval);
  }, [modalOpen, item.runtime.running_jobs, item.connector]);

  const statusBar = [
    { key: "ok"      as CoverageStatus, count: item.status_counts.ok,      color: "var(--color-low)"      },
    { key: "warning" as CoverageStatus, count: item.status_counts.warning,  color: "var(--color-medium)"   },
    { key: "stale"   as CoverageStatus, count: item.status_counts.stale,    color: "var(--color-high)"     },
    { key: "error"   as CoverageStatus, count: item.status_counts.error,    color: "var(--color-critical)" },
    { key: "pending" as CoverageStatus, count: item.status_counts.pending,  color: "var(--color-text-3)"   },
  ].filter((s) => s.count > 0);

  const statusLegend = statusBar.map((s) => s.key === "pending" ? { ...s, color: "var(--color-text-3)" } : s);

  const isRunning = item.runtime.running_jobs > 0;

  return (
    <div
      className="ow-card flex flex-col relative"
      style={{ borderColor: isRunning ? "var(--color-amber-border)" : cfg.borderColor }}
    >
      {isRunning && (
        <span
          className="pointer-events-none absolute inset-0 rounded-xl ring-2 animate-pulse"
          style={{ "--tw-ring-color": "var(--color-amber-border)" } as React.CSSProperties}
        />
      )}

      <div className="flex flex-col gap-4 p-4 flex-1">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="text-label font-bold capitalize leading-snug" style={{ color: "var(--color-text)" }}>
              {item.connector_label}
            </h3>
            <p className="text-mono-xs mt-0.5" style={{ color: "var(--color-text-3)" }}>{item.connector}</p>
          </div>
          <EffectiveBadge item={item} />
        </div>

        {/* Counts */}
        <div className="flex flex-wrap items-center gap-3 text-caption" style={{ color: "var(--color-text-3)" }}>
          <span className="flex items-center gap-1">
            <FileText className="h-3 w-3 shrink-0" />
            <span className="text-mono-xs font-bold" style={{ color: "var(--color-text)" }}>{item.job_count}</span>
            <span>jobs</span>
          </span>
          <span className="flex items-center gap-1" style={{ color: "var(--color-amber-text)" }}>
            <Zap className="h-3 w-3 shrink-0" />
            <span className="text-mono-xs font-bold">{item.enabled_job_count}</span>
            <span>habilitados</span>
          </span>
          {isRunning && (
            <span className="flex items-center gap-1" style={{ color: "var(--color-amber-text)" }}>
              <Activity className="h-3 w-3 shrink-0" />
              {item.runtime.running_jobs} em exec.
            </span>
          )}
          {item.runtime.error_jobs > 0 && (
            <span className="flex items-center gap-1" style={{ color: "var(--color-critical-text)" }}>
              <AlertTriangle className="h-3 w-3 shrink-0" />
              {item.runtime.error_jobs} com erro
            </span>
          )}
        </div>

        {/* Status bar */}
        {totalJobs > 0 && (
          <div className="space-y-1.5">
            <div className="flex h-2 rounded-full overflow-hidden gap-px">
              {statusBar.map((s) => (
                <div
                  key={s.key}
                  style={{ width: `${(s.count / totalJobs) * 100}%`, background: s.color }}
                  title={`${STATUS_CFG[s.key]?.label}: ${s.count}`}
                />
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              {statusLegend.map((s) => (
                <span key={s.key} className="flex items-center gap-1 text-caption" style={{ color: "var(--color-text-3)" }}>
                  <span className="h-1.5 w-1.5 rounded-full" style={{ background: s.color }} />
                  {STATUS_CFG[s.key]?.label}:{" "}
                  <span className="text-mono-xs font-bold" style={{ color: "var(--color-text)" }}>{s.count}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Live progress */}
        {isRunning && (
          <div
            className="rounded-lg border px-3 py-2.5 space-y-2"
            style={{ borderColor: "var(--color-amber-border)", background: "var(--color-amber-dim)" }}
          >
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-caption font-bold uppercase tracking-wider"
                style={{ color: "var(--color-amber-text)" }}>
                <Loader2 className="h-3 w-3 animate-spin" />
                Executando {item.runtime.running_jobs} job(s)
              </span>
              {item.runtime.elapsed_seconds != null && (
                <span className="text-mono-xs" style={{ color: "var(--color-text-3)" }}>
                  {formatElapsed(item.runtime.elapsed_seconds)}
                </span>
              )}
            </div>
            {item.runtime.active_job_names?.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {item.runtime.active_job_names.map((name) => (
                  <span key={name} className="ow-badge ow-badge-amber text-mono-xs">{name}</span>
                ))}
              </div>
            )}
            <div className="flex items-center gap-4 text-caption" style={{ color: "var(--color-text-2)" }}>
              {item.runtime.items_fetched_live > 0 && (
                <span className="text-mono-xs">{item.runtime.items_fetched_live.toLocaleString("pt-BR")} itens coletados</span>
              )}
              {item.runtime.items_normalized_live > 0 && (
                <span className="text-mono-xs">{item.runtime.items_normalized_live.toLocaleString("pt-BR")} normalizados</span>
              )}
              {item.runtime.estimated_rate_per_min != null && item.runtime.estimated_rate_per_min > 0 && (
                <span className="text-mono-xs" style={{ color: "var(--color-amber-text)" }}>
                  ~{item.runtime.estimated_rate_per_min.toLocaleString("pt-BR")}/min
                </span>
              )}
            </div>
          </div>
        )}

        {/* Freshness */}
        <div
          className="rounded-lg border px-3 py-2 space-y-1"
          style={{ borderColor: "var(--color-border)", background: "var(--color-surface-2)" }}
        >
          <div className="flex items-center justify-between text-caption">
            <span className="flex items-center gap-1" style={{ color: "var(--color-text-3)" }}>
              <Clock className="h-3 w-3" />
              Último sucesso
            </span>
            {item.max_freshness_lag_hours != null && (
              <span className="text-mono-xs font-bold" style={{ color: lagColor(item.max_freshness_lag_hours) }}>
                {formatLag(item.max_freshness_lag_hours)} defasagem
              </span>
            )}
          </div>
          <p className="text-mono-xs" style={{ color: "var(--color-text)" }}>
            {item.last_success_at
              ? new Date(item.last_success_at).toLocaleString("pt-BR")
              : "Sem execução registrada"}
          </p>
        </div>

        {/* Stuck warning */}
        {item.runtime.stuck_jobs > 0 && (
          <div className="ow-alert ow-alert-error">
            <AlertTriangle className="h-3 w-3 shrink-0" />
            {item.runtime.stuck_jobs} job(s) travado(s) — restart recomendado
          </div>
        )}
      </div>

      {/* Diagnose button */}
      <button
        onClick={handleOpenModal}
        className="flex w-full items-center justify-center gap-1.5 border-t px-4 py-2.5 text-caption font-semibold transition-colors"
        style={{
          borderColor: "var(--color-border)",
          color: "var(--color-text-3)",
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = "var(--color-surface-3)";
          (e.currentTarget as HTMLButtonElement).style.color = "var(--color-text)";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = "";
          (e.currentTarget as HTMLButtonElement).style.color = "var(--color-text-3)";
        }}
      >
        <FileText className="h-3.5 w-3.5" />
        Ver diagnóstico detalhado
      </button>

      {modalOpen && (
        <SourceDiagnosticModal
          item={item}
          preview={preview}
          loading={previewLoading}
          error={previewError}
          onClose={() => setModalOpen(false)}
        />
      )}
    </div>
  );
}

// ── Run state helper ──────────────────────────────────────────────────────────

function getRunState(item: AnalyticalCoverageItem): {
  label: string;
  color: string;
  detail: string | null;
} {
  if (item.last_run_status === "error") {
    return {
      label: "Erro na execução",
      color: "var(--color-critical-text)",
      detail: item.last_run_error_message ?? null,
    };
  }
  if (item.last_run_status === "success") {
    const candidates = item.last_run_candidates ?? 0;
    const created = item.last_run_signals_created ?? 0;
    if (candidates === 0) {
      return {
        label: "Sem dados de entrada",
        color: "var(--color-medium-text)",
        detail: item.domains_missing?.length
          ? `Domínios em falta: ${item.domains_missing.join(", ")}`
          : null,
      };
    }
    if (created === 0) {
      return {
        label: "Sem sinais qualificados",
        color: "var(--color-text-2)",
        detail: `${candidates} candidatos avaliados`,
      };
    }
    return {
      label: `${created} sinal${created !== 1 ? "s" : ""} gerado${created !== 1 ? "s" : ""}`,
      color: "var(--color-low-text)",
      detail: null,
    };
  }
  if (item.last_run_status === "running") {
    return { label: "Em execução...", color: "var(--color-amber-text)", detail: null };
  }
  return { label: "Nunca executado", color: "var(--color-text-3)", detail: null };
}

// ── Typology info modal ───────────────────────────────────────────────────────

function TypologyInfoModal({ item, onClose }: { item: AnalyticalCoverageItem; onClose: () => void }) {
  const domainTotal = item.required_domains.length;
  const domainAvail = item.domains_available.length;
  const pct = domainTotal > 0 ? Math.round((domainAvail / domainTotal) * 100) : 0;
  const barColor = item.apt ? "var(--color-low)" : pct > 0 ? "var(--color-high)" : "var(--color-critical)";

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 backdrop-blur-sm"
        style={{ background: "rgba(0,0,0,0.7)" }}
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        className="relative z-10 flex w-full max-w-2xl max-h-[88vh] flex-col rounded-2xl border shadow-2xl overflow-hidden"
        style={{ background: "var(--color-surface)", borderColor: "var(--color-border-strong)" }}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b px-6 py-4"
          style={{ borderColor: "var(--color-border)" }}>
          <div>
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <span className="ow-badge ow-badge-neutral text-mono-xs">{item.typology_code}</span>
              {item.apt ? (
                <span className="ow-badge ow-badge-low">Apta</span>
              ) : (
                <span className="ow-badge ow-badge-critical">Bloqueada</span>
              )}
            </div>
            <h2 className="text-display-sm font-bold" style={{ color: "var(--color-text)" }}>
              {item.typology_name}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border transition-colors"
            style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)", color: "var(--color-text-3)" }}
            aria-label="Fechar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Summary strip */}
        <div className="grid grid-cols-3 gap-3 border-b px-6 py-4"
          style={{ borderColor: "var(--color-border)" }}>
          {[
            { label: "Evidência",   value: item.evidence_level ?? "—",     color: "var(--color-text)" },
            { label: "Domínios",    value: `${domainAvail}/${domainTotal}`, color: "var(--color-text)", sub: `${pct}% coberto` },
            { label: "Sinais 30d",  value: item.signals_30d,               color: item.signals_30d > 0 ? "var(--color-low-text)" : "var(--color-text-3)" },
          ].map((m) => (
            <div key={m.label}>
              <p className="text-mono-xs uppercase tracking-widest mb-1" style={{ color: "var(--color-text-3)" }}>{m.label}</p>
              <p className="text-mono font-bold leading-none capitalize" style={{ color: m.color }}>{m.value}</p>
              {m.sub && <p className="text-mono-xs mt-0.5" style={{ color: "var(--color-text-3)" }}>{m.sub}</p>}
            </div>
          ))}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6"
          style={{ background: "var(--color-surface-2)" }}>

          {item.description_legal && (
            <section>
              <p className="text-mono-xs uppercase tracking-widest mb-3" style={{ color: "var(--color-text-3)" }}>
                Descrição Legal
              </p>
              <div className="ow-alert ow-alert-info">
                <Lightbulb className="h-4 w-4 shrink-0 mt-0.5" />
                <p className="text-body leading-relaxed">{item.description_legal}</p>
              </div>
            </section>
          )}

          <section>
            <p className="text-mono-xs uppercase tracking-widest mb-3" style={{ color: "var(--color-text-3)" }}>
              Domínios de Dados Necessários
            </p>
            <div className="ow-card p-4 space-y-3">
              <div className="ow-score-bar-track">
                <div className="ow-score-bar-fill transition-all" style={{ width: `${pct}%`, background: barColor }} />
              </div>
              <div className="flex flex-wrap gap-2">
                {item.domains_available.map((d) => (
                  <span key={d} className="ow-badge ow-badge-low">
                    <CheckCircle2 className="h-3 w-3 mr-1" />{d}
                  </span>
                ))}
                {item.domains_missing.map((d) => (
                  <span key={d} className="ow-badge ow-badge-critical">
                    <XCircle className="h-3 w-3 mr-1" />{d}
                  </span>
                ))}
              </div>
              {item.domains_missing.length > 0 && (
                <p className="text-caption leading-relaxed" style={{ color: "var(--color-text-3)" }}>
                  {item.domains_missing.length === 1
                    ? "1 domínio ausente — tipologia bloqueada até todos os domínios estarem disponíveis."
                    : `${item.domains_missing.length} domínios ausentes — tipologia bloqueada até todos os domínios estarem disponíveis.`}
                </p>
              )}
            </div>
          </section>

          {((item.corruption_types && item.corruption_types.length > 0) || (item.spheres && item.spheres.length > 0)) && (
            <section>
              <p className="text-mono-xs uppercase tracking-widest mb-3" style={{ color: "var(--color-text-3)" }}>
                Classificação Jurídica
              </p>
              <div className="ow-card p-4 space-y-4">
                {item.corruption_types && item.corruption_types.length > 0 && (
                  <div>
                    <p className="text-caption mb-2" style={{ color: "var(--color-text-3)" }}>
                      Tipos de corrupção cobertos
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {item.corruption_types.map((ct) => (
                        <span key={ct} className="ow-badge ow-badge-neutral capitalize">
                          {ct.replace(/_/g, " ")}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {item.spheres && item.spheres.length > 0 && (
                  <div>
                    <p className="text-caption mb-2" style={{ color: "var(--color-text-3)" }}>Esferas</p>
                    <div className="flex flex-wrap gap-1.5">
                      {item.spheres.map((s) => (
                        <span key={s} className="ow-badge ow-badge-amber capitalize">{s}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </section>
          )}

          {item.last_run_at && (
            <section>
              <p className="text-mono-xs uppercase tracking-widest mb-3" style={{ color: "var(--color-text-3)" }}>
                Última Execução
              </p>
              <div className="ow-card p-4 grid grid-cols-2 gap-3">
                <div>
                  <p className="text-mono-xs mb-0.5" style={{ color: "var(--color-text-3)" }}>Data</p>
                  <p className="text-mono-xs" style={{ color: "var(--color-text)" }}>
                    {new Date(item.last_run_at).toLocaleString("pt-BR")}
                  </p>
                </div>
                <div>
                  <p className="text-mono-xs mb-0.5" style={{ color: "var(--color-text-3)" }}>Status</p>
                  {(() => {
                    const state = getRunState(item);
                    return (
                      <div>
                        <p className="text-mono-xs font-semibold" style={{ color: state.color }}>{state.label}</p>
                        {state.detail && (
                          <p className="mt-0.5 text-caption" style={{ color: "var(--color-text-3)" }}>{state.detail}</p>
                        )}
                      </div>
                    );
                  })()}
                </div>
                {item.last_run_candidates != null && item.last_run_candidates > 0 && (
                  <div>
                    <p className="text-mono-xs mb-0.5" style={{ color: "var(--color-text-3)" }}>Candidatos</p>
                    <p className="text-mono-xs font-bold" style={{ color: "var(--color-text)" }}>
                      {item.last_run_candidates}
                    </p>
                  </div>
                )}
                {item.last_run_signals_created != null && (
                  <div>
                    <p className="text-mono-xs mb-0.5" style={{ color: "var(--color-text-3)" }}>Sinais criados</p>
                    <p className="text-mono-xs font-bold" style={{ color: "var(--color-text)" }}>
                      {item.last_run_signals_created}
                    </p>
                  </div>
                )}
              </div>
            </section>
          )}
        </div>

        <div className="flex items-center justify-end border-t px-6 py-3"
          style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}>
          <Button variant="ghost" size="sm" onClick={onClose}>Fechar</Button>
        </div>
      </div>
    </div>
  );
}

// ── Typology card ─────────────────────────────────────────────────────────────

function TypologyCard({ item }: { item: AnalyticalCoverageItem }) {
  const [modalOpen, setModalOpen] = useState(false);
  const domainTotal = item.required_domains.length;
  const domainAvail = item.domains_available.length;
  const pct = domainTotal > 0 ? Math.round((domainAvail / domainTotal) * 100) : 0;
  const barColor = item.apt ? "var(--color-low)" : pct > 0 ? "var(--color-high)" : "var(--color-critical)";
  const borderColor = item.apt ? "var(--color-low-border)" : pct > 0 ? "var(--color-high-border)" : "var(--color-critical-border)";

  return (
    <div className="ow-card flex flex-col" style={{ borderColor }}>
      <div className="p-4 space-y-3 flex-1">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className="ow-badge ow-badge-neutral text-mono-xs">{item.typology_code}</span>
              {item.apt ? (
                item.signals_30d > 0 ? (
                  <span className="ow-badge ow-badge-low">Ativa · {item.signals_30d} sinais/30d</span>
                ) : (
                  <span className="ow-badge ow-badge-low">Apta</span>
                )
              ) : (
                <span className="ow-badge ow-badge-critical">Bloqueada</span>
              )}
            </div>
            <p className="text-caption font-semibold leading-snug" style={{ color: "var(--color-text)" }}>
              {item.typology_name}
            </p>
          </div>
          <span className="text-mono font-bold shrink-0" style={{ color: "var(--color-text)" }}>{pct}%</span>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <p className="text-caption" style={{ color: "var(--color-text-3)" }}>Domínios cobertos</p>
            <p className="text-caption" style={{ color: "var(--color-text-3)" }}>{domainAvail}/{domainTotal}</p>
          </div>
          <div className="ow-score-bar-track">
            <div className="ow-score-bar-fill transition-all" style={{ width: `${pct}%`, background: barColor }} />
          </div>
        </div>

        {(item.domains_available.length > 0 || item.domains_missing.length > 0) && (
          <div className="flex flex-wrap gap-1">
            {item.domains_available.map((d) => (
              <span key={d} className="ow-badge ow-badge-low">{d}</span>
            ))}
            {item.domains_missing.map((d) => (
              <span key={d} className="ow-badge ow-badge-critical line-through opacity-70">{d}</span>
            ))}
          </div>
        )}

        {(item.last_run_at || item.last_run_candidates != null || item.signals_30d > 0) && (
          <div
            className="grid grid-cols-2 gap-x-3 gap-y-1 border-t pt-2"
            style={{ borderColor: "var(--color-border)" }}
          >
            {item.signals_30d > 0 && (
              <div className="text-caption">
                <span style={{ color: "var(--color-text-3)" }}>Sinais 30d: </span>
                <span className="text-mono-xs font-bold" style={{ color: "var(--color-text)" }}>{item.signals_30d}</span>
              </div>
            )}
            {item.last_run_candidates != null && item.last_run_candidates > 0 && (
              <div className="text-caption">
                <span style={{ color: "var(--color-text-3)" }}>Candidatos: </span>
                <span className="text-mono-xs font-bold" style={{ color: "var(--color-text)" }}>{item.last_run_candidates}</span>
              </div>
            )}
            {item.last_run_signals_created != null && (
              <div className="text-caption">
                <span style={{ color: "var(--color-text-3)" }}>Criados: </span>
                <span className="text-mono-xs font-bold" style={{ color: "var(--color-text)" }}>{item.last_run_signals_created}</span>
              </div>
            )}
            {item.last_run_signals_deduped != null && item.last_run_signals_deduped > 0 && (
              <div className="text-caption">
                <span style={{ color: "var(--color-text-3)" }}>Deduped: </span>
                <span className="text-mono-xs font-bold" style={{ color: "var(--color-text)" }}>{item.last_run_signals_deduped}</span>
              </div>
            )}
            {item.last_run_at && (
              <div className="col-span-2 text-caption">
                <span style={{ color: "var(--color-text-3)" }}>Última exec.: </span>
                <span className="text-mono-xs" style={{ color: "var(--color-text)" }}>
                  {new Date(item.last_run_at).toLocaleString("pt-BR")}
                </span>
                {(() => {
                  const state = getRunState(item);
                  return (
                    <span className="ml-1.5 inline-flex items-center gap-1">
                      <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ background: state.color }} />
                      <span className="text-mono-xs font-bold" style={{ color: state.color }}>{state.label}</span>
                    </span>
                  );
                })()}
              </div>
            )}
          </div>
        )}

        {(item.evidence_level || (item.corruption_types && item.corruption_types.length > 0)) && (
          <div className="flex flex-wrap gap-1 border-t pt-2" style={{ borderColor: "var(--color-border)" }}>
            {item.evidence_level && (
              <span className="ow-badge ow-badge-neutral capitalize">{item.evidence_level}</span>
            )}
            {item.corruption_types?.slice(0, 2).map((ct) => (
              <span key={ct} className="ow-badge ow-badge-neutral">{ct}</span>
            ))}
          </div>
        )}
      </div>

      <button
        onClick={() => setModalOpen(true)}
        className="flex w-full items-center justify-center gap-1.5 border-t px-4 py-2.5 text-caption font-semibold transition-colors"
        style={{ borderColor: "var(--color-border)", color: "var(--color-text-3)" }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = "var(--color-surface-3)";
          (e.currentTarget as HTMLButtonElement).style.color = "var(--color-text)";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = "";
          (e.currentTarget as HTMLButtonElement).style.color = "var(--color-text-3)";
        }}
      >
        <BookOpen className="h-3.5 w-3.5" />
        Ver detalhes da tipologia
      </button>

      {modalOpen && <TypologyInfoModal item={item} onClose={() => setModalOpen(false)} />}
    </div>
  );
}

// ── Pipeline Modal ────────────────────────────────────────────────────────────

type StageKey = "ingest" | "entity_resolution" | "signals";
type StageStatus = "idle" | "dispatching" | "dispatched" | "error";

interface StageState {
  status: StageStatus;
  taskId?: string;
}

const PIPELINE_STAGE_DEFS: { key: StageKey; label: string; description: string; worker: string }[] = [
  {
    key: "ingest",
    label: "Ingestão de Dados",
    description: "Coleta incremental de todas as fontes públicas federais",
    worker: "worker-ingest",
  },
  {
    key: "entity_resolution",
    label: "Resolução de Entidades",
    description: "Deduplicação e agrupamento de CPF/CNPJ entre fontes",
    worker: "worker-er",
  },
  {
    key: "signals",
    label: "Sinais de Risco",
    description: "Execução das 22 tipologias de corrupção detectadas",
    worker: "worker-cpu",
  },
];

function PipelineModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [stages, setStages] = useState<Record<StageKey, StageState>>({
    ingest: { status: "idle" },
    entity_resolution: { status: "idle" },
    signals: { status: "idle" },
  });
  const [running, setRunning] = useState(false);
  const [checking, setChecking] = useState(false);
  const [alreadyRunning, setAlreadyRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const allDispatched = Object.values(stages).every((s) => s.status === "dispatched");

  useEffect(() => {
    if (!open) return;
    setChecking(true);
    setAlreadyRunning(false);
    setError(null);
    setStages({ ingest: { status: "idle" }, entity_resolution: { status: "idle" }, signals: { status: "idle" } });
    getPipelineStatus()
      .then((status: PipelineStatusResponse) => {
        if (status.is_running) {
          setAlreadyRunning(true);
          setStages({
            ingest: { status: status.stages.ingest === "running" ? "dispatched" : "idle" },
            entity_resolution: { status: status.stages.entity_resolution === "running" ? "dispatched" : "idle" },
            signals: { status: status.stages.signals === "running" ? "dispatched" : "idle" },
          });
        }
      })
      .catch(() => { /* status check is best-effort */ })
      .finally(() => setChecking(false));
  }, [open]);

  function resetAndClose() {
    setStages({ ingest: { status: "idle" }, entity_resolution: { status: "idle" }, signals: { status: "idle" } });
    setRunning(false);
    setAlreadyRunning(false);
    setError(null);
    onClose();
  }

  async function handleExecute() {
    if (running) return;
    setRunning(true);
    setError(null);
    setStages({ ingest: { status: "dispatching" }, entity_resolution: { status: "dispatching" }, signals: { status: "dispatching" } });
    try {
      const result: PipelineDispatchResponse = await triggerFullPipeline();
      setStages({
        ingest: { status: "dispatched", taskId: result.stages.ingest.task_id },
        entity_resolution: { status: "dispatched", taskId: result.stages.entity_resolution.task_id },
        signals: { status: "dispatched", taskId: result.stages.signals.task_id },
      });
    } catch (e) {
      if (e instanceof Error && e.message.includes("409")) {
        setAlreadyRunning(true);
        setStages({ ingest: { status: "idle" }, entity_resolution: { status: "idle" }, signals: { status: "idle" } });
      } else {
        setError(e instanceof Error ? e.message : "Erro ao disparar o pipeline.");
        setStages({ ingest: { status: "error" }, entity_resolution: { status: "error" }, signals: { status: "error" } });
      }
    } finally {
      setRunning(false);
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 backdrop-blur-sm"
        style={{ background: "rgba(0,0,0,0.7)" }}
        onClick={!running ? resetAndClose : undefined}
      />
      <div
        className="relative w-full max-w-md rounded-2xl border shadow-2xl"
        style={{ background: "var(--color-surface)", borderColor: "var(--color-border-strong)" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4"
          style={{ borderColor: "var(--color-border)" }}>
          <div className="flex items-center gap-3">
            <div
              className="flex h-8 w-8 items-center justify-center rounded-lg border"
              style={{ background: "var(--color-amber-dim)", borderColor: "var(--color-amber-border)" }}
            >
              <Zap className="h-4 w-4" style={{ color: "var(--color-amber-text)" }} />
            </div>
            <div>
              <p className="text-label font-semibold" style={{ color: "var(--color-text)" }}>Executar Pipeline</p>
              <p className="text-caption" style={{ color: "var(--color-text-3)" }}>Ingestão → ER → Sinais de Risco</p>
            </div>
          </div>
          <button
            onClick={resetAndClose}
            className="rounded-lg p-1.5 transition-colors"
            style={{ color: "var(--color-text-3)" }}
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {alreadyRunning && (
          <div className="mx-6 mt-5">
            <div className="ow-alert ow-alert-warning">
              <Activity className="h-4 w-4 shrink-0 mt-0.5" />
              <div>
                <p className="text-label font-semibold">Pipeline já em execução</p>
                <p className="mt-0.5 text-caption">
                  Os workers já estão processando dados. Aguarde a conclusão do ciclo atual.
                </p>
              </div>
            </div>
          </div>
        )}

        {checking && (
          <div className="flex items-center justify-center gap-2 py-6 text-caption"
            style={{ color: "var(--color-text-3)" }}>
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Verificando estado do pipeline...
          </div>
        )}

        {!checking && (
          <div className="px-6 py-5 space-y-3">
            {PIPELINE_STAGE_DEFS.map((def, i) => {
              const stage = stages[def.key];
              const isActive = alreadyRunning && stage.status === "dispatched";
              const isDispatched = !alreadyRunning && stage.status === "dispatched";
              const isDispatching = stage.status === "dispatching";
              const isError = stage.status === "error";

              const stageBorderColor = isActive
                ? "var(--color-amber-border)"
                : isDispatched
                ? "var(--color-low-border)"
                : isError
                ? "var(--color-critical-border)"
                : "var(--color-border)";
              const stageBg = isActive
                ? "var(--color-amber-dim)"
                : isDispatched
                ? "var(--color-low-bg)"
                : isError
                ? "var(--color-critical-bg)"
                : "var(--color-surface-2)";

              return (
                <div
                  key={def.key}
                  className="flex items-start gap-3 rounded-xl border p-3.5 transition-all duration-300"
                  style={{ borderColor: stageBorderColor, background: stageBg }}
                >
                  <div
                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-mono-xs font-bold transition-all duration-300 border"
                    style={{
                      background: isDispatched ? "var(--color-low)" : isError ? "var(--color-critical)" : "var(--color-surface)",
                      borderColor: isActive ? "var(--color-amber-border)" : "var(--color-border)",
                      color: isDispatched || isError ? "white" : isActive ? "var(--color-amber-text)" : "var(--color-text-3)",
                    }}
                  >
                    {isDispatching ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : isActive ? (
                      <Activity className="h-3.5 w-3.5" />
                    ) : isDispatched ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : isError ? (
                      <XCircle className="h-3.5 w-3.5" />
                    ) : (
                      <span>{i + 1}</span>
                    )}
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <p
                        className="text-label font-semibold"
                        style={{
                          color: isActive
                            ? "var(--color-amber-text)"
                            : isDispatched
                            ? "var(--color-low-text)"
                            : isError
                            ? "var(--color-critical-text)"
                            : "var(--color-text)",
                        }}
                      >
                        {def.label}
                        {isActive && (
                          <span className="ml-2 text-mono-xs font-normal" style={{ color: "var(--color-amber-text)", opacity: 0.7 }}>
                            em execução
                          </span>
                        )}
                      </p>
                      <span
                        className="text-mono-xs px-1.5 py-0.5 rounded border shrink-0"
                        style={{ borderColor: "var(--color-border)", background: "var(--color-surface)", color: "var(--color-text-3)" }}
                      >
                        {def.worker}
                      </span>
                    </div>
                    <p className="mt-0.5 text-caption" style={{ color: "var(--color-text-2)" }}>{def.description}</p>
                    {isDispatched && stage.taskId && (
                      <p className="mt-1.5 text-mono-xs truncate" style={{ color: "var(--color-low-text)", opacity: 0.7 }}>
                        task: {stage.taskId}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {error && (
          <div className="mx-6 mb-4">
            <div className="ow-alert ow-alert-error">{error}</div>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t px-6 py-4"
          style={{ borderColor: "var(--color-border)" }}>
          {alreadyRunning ? (
            <div className="flex w-full items-center justify-between">
              <p className="flex items-center gap-1.5 text-caption" style={{ color: "var(--color-text-2)" }}>
                <Clock className="h-3.5 w-3.5" />
                O pipeline conclui automaticamente
              </p>
              <Button variant="ghost" size="sm" onClick={resetAndClose}>Fechar</Button>
            </div>
          ) : allDispatched ? (
            <div className="flex w-full items-center justify-between">
              <p className="flex items-center gap-1.5 text-caption font-semibold" style={{ color: "var(--color-low-text)" }}>
                <CheckCircle2 className="h-4 w-4" />
                Pipeline iniciado com sucesso
              </p>
              <Button variant="ghost" size="sm" onClick={resetAndClose}>Fechar</Button>
            </div>
          ) : (
            <>
              <Button variant="ghost" size="sm" onClick={resetAndClose} disabled={running}>
                Cancelar
              </Button>
              <Button
                variant="amber"
                size="sm"
                onClick={handleExecute}
                disabled={running || checking}
                loading={running}
              >
                {!running && <Play className="h-3.5 w-3.5" />}
                {running ? "Iniciando..." : "Executar"}
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CoveragePage() {
  const [summary, setSummary] = useState<CoverageV2SummaryResponse | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  const [sources, setSources] = useState<CoverageV2SourceItem[]>([]);
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [sourcesError, setSourcesError] = useState<string | null>(null);

  const [analytics, setAnalytics] = useState<CoverageV2AnalyticsResponse | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(true);

  const [capacity, setCapacity] = useState<PipelineCapacity | null>(null);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"" | CoverageStatus>("");
  const [enabledOnly, setEnabledOnly] = useState(false);

  const [pipelineModalOpen, setPipelineModalOpen] = useState(false);
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => {
    let active = true;
    setSummaryLoading(true);
    const fetchSummary = () =>
      getCoverageV2Summary()
        .then((d) => { if (active) setSummary(d); })
        .catch(() => { if (active) setSummaryError("Não foi possível carregar o resumo da cobertura."); })
        .finally(() => { if (active) setSummaryLoading(false); });
    fetchSummary();
    const interval = setInterval(fetchSummary, 10_000);
    return () => { active = false; clearInterval(interval); };
  }, [refreshTick]);

  useEffect(() => {
    let active = true;
    function fetchSources() {
      getCoverageV2Sources({ limit: 100, enabled_only: enabledOnly })
        .then((r) => { if (active) setSources(r.items); })
        .catch(() => { if (active) setSourcesError("Falha ao carregar fontes de dados."); })
        .finally(() => { if (active) setSourcesLoading(false); });
    }
    setSourcesLoading(true);
    fetchSources();
    const hasRunning = sources?.some((s) => s.runtime.running_jobs > 0);
    const interval = setInterval(fetchSources, hasRunning ? 5_000 : 15_000);
    return () => { active = false; clearInterval(interval); };
  }, [enabledOnly, sources?.some((s) => s.runtime.running_jobs > 0), refreshTick]);

  useEffect(() => {
    let active = true;
    getCoverageV2Analytics()
      .then((d) => { if (active) setAnalytics(d); })
      .catch(() => {})
      .finally(() => { if (active) setAnalyticsLoading(false); });
    return () => { active = false; };
  }, [refreshTick]);

  useEffect(() => {
    let active = true;
    getPipelineCapacity()
      .then((d) => { if (active) setCapacity(d); })
      .catch(() => {});
    return () => { active = false; };
  }, [refreshTick]);

  const filteredSources = useMemo(() => {
    return sources
      .filter((s) => {
        if (statusFilter && s.worst_status !== statusFilter) return false;
        if (search.trim()) {
          const q = search.toLowerCase();
          if (!s.connector_label.toLowerCase().includes(q) && !s.connector.toLowerCase().includes(q)) return false;
        }
        return true;
      })
      .sort((a, b) => {
        const aRunning = a.runtime.running_jobs > 0 ? 0 : 1;
        const bRunning = b.runtime.running_jobs > 0 ? 0 : 1;
        if (aRunning !== bRunning) return aRunning - bRunning;
        const order: CoverageStatus[] = ["error", "warning", "stale", "ok", "pending"];
        return order.indexOf(a.worst_status) - order.indexOf(b.worst_status);
      });
  }, [sources, search, statusFilter]);

  return (
    <div className="min-h-screen" style={{ background: "var(--color-surface-2)" }}>

      {/* ── Page Header ─────────────────────────────────────────── */}
      <PageHeader
        eyebrow="SISTEMA"
        title="Cobertura de Dados"
        description={
          summary?.snapshot_at
            ? `Snapshot: ${new Date(summary.snapshot_at).toLocaleString("pt-BR")} · Estado operacional do pipeline e qualidade das fontes públicas federais`
            : "Estado operacional do pipeline de ingestão e qualidade das fontes públicas federais"
        }
        variant="hero"
        icon={<Database className="h-5 w-5" />}
        stats={[
          {
            label: "Fontes",
            value: summaryLoading ? "—" : formatNumber(summary?.totals?.connectors ?? 0),
            mono: true,
            tone: "brand",
          },
          {
            label: "Jobs ativos",
            value: summaryLoading ? "—" : formatNumber(summary?.totals?.jobs_enabled ?? 0),
            sub: summaryLoading ? undefined : `${summary?.totals?.jobs ?? 0} jobs`,
            mono: true,
          },
          {
            label: "Operacionais",
            value: summaryLoading ? "—" : formatNumber(summary?.totals?.status_counts?.ok ?? 0),
            mono: true,
            tone: "success",
          },
          {
            label: "Alertas",
            value: summaryLoading ? "—" : formatNumber((summary?.totals?.status_counts?.warning ?? 0) + (summary?.totals?.status_counts?.stale ?? 0) + (summary?.totals?.status_counts?.error ?? 0)),
            sub: summaryLoading ? undefined : `${summary?.totals?.runtime?.failed_or_stuck ?? 0} travados`,
            mono: true,
            tone: ((summary?.totals?.status_counts?.error ?? 0) > 0 || (summary?.totals?.runtime?.failed_or_stuck ?? 0) > 0) ? "danger" : "warning",
          },
        ]}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setRefreshTick((t) => t + 1)}
              disabled={summaryLoading}
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Atualizar
            </Button>
            <Button
              variant="amber"
              size="sm"
              onClick={() => setPipelineModalOpen(true)}
            >
              <Zap className="h-3.5 w-3.5" />
              Executar Pipeline
            </Button>
          </div>
        }
      />

      {/* ── KPI Strip ────────────────────────────────────────────── */}
      <div className="border-b" style={{ borderColor: "var(--color-border)" }}>
        <div className="mx-auto max-w-[1280px] px-4 py-4 sm:px-6">
          <KpiStrip summary={summary} loading={summaryLoading} />
        </div>
      </div>

      {/* ── Body ────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6 space-y-8 animate-fade-in">

        {summaryError && (
          <div className="ow-alert ow-alert-error">{summaryError}</div>
        )}

        {/* Pipeline stages */}
        {!summaryLoading && summary && <PipelineStrip summary={summary} />}

        {/* Capacity metrics */}
        {capacity && (
          <section className="ow-card p-5">
            <p className="text-mono-xs uppercase tracking-widest mb-4" style={{ color: "var(--color-text-3)" }}>
              Capacidade do Pipeline
            </p>
            <div className="ow-strip">
              {Object.entries(capacity).map(([key, val]) => (
                <div key={key} className="ow-strip-item">
                  <span className="ow-strip-value text-mono">{String(val)}</span>
                  <span className="ow-strip-label">{key.replace(/_/g, " ")}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ── Live Activity Panel ──────────────────────────────── */}
        {!sourcesLoading && (() => {
          const activeJobs = sources
            .filter(s => s.runtime.running_jobs > 0)
            .flatMap(s => s.runtime.active_job_names.map(job => ({
              connector: s.connector_label,
              connectorKey: s.connector,
              job,
              itemsLive: s.runtime.items_fetched_live,
              rate: s.runtime.estimated_rate_per_min,
              elapsed: s.runtime.elapsed_seconds,
            })));
          const errorJobs = sources.filter(s => s.runtime.error_jobs > 0);
          const pendingSources = sources.filter(s => s.worst_status === "pending" && s.runtime.running_jobs === 0);
          const totalRunning = activeJobs.length;
          const pipelineStages = summary?.pipeline.stages ?? [];
          const nextStage = pipelineStages.find(s => s.status === "stale" || s.status === "pending");

          return (totalRunning > 0 || errorJobs.length > 0) ? (
            <section className="ow-card p-5 space-y-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div
                    className="flex h-8 w-8 items-center justify-center rounded-lg"
                    style={{ background: "var(--color-surface-3)" }}
                  >
                    <Activity className="h-4 w-4" style={{ color: "var(--color-text-3)" }} />
                  </div>
                  <p className="text-mono-xs uppercase tracking-widest" style={{ color: "var(--color-text-3)" }}>
                    O que está acontecendo agora?
                  </p>
                </div>
                <span className="ow-badge ow-badge-amber">
                  <span className="inline-block h-1.5 w-1.5 rounded-full mr-1 animate-pulse" style={{ background: "var(--color-amber)" }} />
                  {totalRunning} job{totalRunning !== 1 ? "s" : ""} ativo{totalRunning !== 1 ? "s" : ""}
                </span>
              </div>

              <div className="space-y-2">
                {activeJobs.map((aj) => (
                  <div
                    key={`${aj.connectorKey}-${aj.job}`}
                    className="flex items-center justify-between gap-3 rounded-lg border px-4 py-2.5"
                    style={{ borderColor: "var(--color-amber-border)", background: "var(--color-amber-dim)" }}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="h-2 w-2 rounded-full animate-pulse shrink-0" style={{ background: "var(--color-amber)" }} />
                      <p className="text-mono-xs font-bold truncate" style={{ color: "var(--color-text)" }}>
                        {aj.connector}{" "}
                        <span style={{ color: "var(--color-text-3)", fontWeight: "normal" }}>/ {aj.job}</span>
                      </p>
                    </div>
                    <div className="flex items-center gap-4 shrink-0 text-mono-xs" style={{ color: "var(--color-text-3)" }}>
                      {aj.itemsLive > 0 && (
                        <span className="font-bold" style={{ color: "var(--color-text)" }}>
                          {aj.itemsLive.toLocaleString("pt-BR")} itens
                        </span>
                      )}
                      {aj.rate != null && aj.rate > 0 && (
                        <span style={{ color: "var(--color-amber-text)" }}>~{Math.round(aj.rate).toLocaleString("pt-BR")}/min</span>
                      )}
                      {aj.elapsed != null && <span>{formatElapsed(aj.elapsed)}</span>}
                    </div>
                  </div>
                ))}
              </div>

              {errorJobs.length > 0 && (
                <div className="ow-alert ow-alert-error">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <div>
                    <p className="text-mono-xs font-bold mb-1.5">
                      {errorJobs.reduce((n, s) => n + s.runtime.error_jobs, 0)} job(s) com erro
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {errorJobs.map(s => (
                        <span key={s.connector} className="ow-badge ow-badge-critical text-mono-xs">
                          {s.connector_label} ({s.runtime.error_jobs})
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              <div
                className="rounded-lg border px-4 py-3"
                style={{ borderColor: "var(--color-border)", background: "var(--color-surface-2)" }}
              >
                <p className="text-mono-xs uppercase tracking-widest mb-2" style={{ color: "var(--color-text-3)" }}>
                  O que vem depois?
                </p>
                <div className="space-y-1.5 text-caption" style={{ color: "var(--color-text-2)" }}>
                  {nextStage && (
                    <div className="flex items-center gap-2">
                      <span className="h-1.5 w-1.5 rounded-full shrink-0" style={{ background: "var(--color-high)" }} />
                      <span>
                        Próxima etapa:{" "}
                        <strong style={{ color: "var(--color-text)" }}>{nextStage.label}</strong>{" "}
                        — {nextStage.reason}
                      </span>
                    </div>
                  )}
                  {pendingSources.length > 0 && (
                    <div className="flex items-center gap-2">
                      <span className="h-1.5 w-1.5 rounded-full shrink-0" style={{ background: "var(--color-text-3)" }} />
                      <span>
                        {pendingSources.length} fonte(s) aguardando:{" "}
                        <span className="text-mono-xs" style={{ color: "var(--color-text-3)" }}>
                          {pendingSources.slice(0, 4).map(s => s.connector_label).join(", ")}
                          {pendingSources.length > 4 ? ` +${pendingSources.length - 4}` : ""}
                        </span>
                      </span>
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full shrink-0" style={{ background: "var(--color-amber)", opacity: 0.5 }} />
                    <span>Após ingestão: Resolução de Entidades → Baselines → Detecção de Sinais → Geração de Cases</span>
                  </div>
                </div>
              </div>
            </section>
          ) : null;
        })()}

        {/* ── Sources section ──────────────────────────────────── */}
        <section className="ow-card p-5">
          <div className="flex flex-wrap items-end justify-between gap-3 mb-5">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg shrink-0"
                style={{ background: "var(--color-surface-3)" }}>
                <Database className="h-4 w-4" style={{ color: "var(--color-text-3)" }} />
              </div>
              <p className="text-mono-xs uppercase tracking-widest" style={{ color: "var(--color-text-3)" }}>
                Fontes de Dados
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <label
                className="flex items-center gap-2 rounded-lg border px-3 py-1.5"
                style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}
              >
                <Search className="h-3.5 w-3.5 shrink-0" style={{ color: "var(--color-text-3)" }} />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Buscar fonte..."
                  className="w-36 bg-transparent text-caption outline-none"
                  style={{ color: "var(--color-text)" }}
                />
              </label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as "" | CoverageStatus)}
                className="rounded-lg border px-3 py-1.5 text-caption outline-none"
                style={{
                  borderColor: "var(--color-border)",
                  background: "var(--color-surface)",
                  color: "var(--color-text)",
                }}
              >
                <option value="">Todos os status</option>
                <option value="ok">OK</option>
                <option value="warning">Atenção</option>
                <option value="stale">Defasado</option>
                <option value="error">Erro</option>
                <option value="pending">Pendente</option>
              </select>
              <label
                className="flex items-center gap-2 rounded-lg border px-3 py-1.5 cursor-pointer text-caption"
                style={{
                  borderColor: "var(--color-border)",
                  background: "var(--color-surface)",
                  color: "var(--color-text-2)",
                }}
              >
                <input
                  type="checkbox"
                  checked={enabledOnly}
                  onChange={(e) => setEnabledOnly(e.target.checked)}
                  className="h-3 w-3"
                />
                Apenas habilitados
              </label>
            </div>
          </div>

          {sourcesError && (
            <div className="ow-alert ow-alert-error mb-4">{sourcesError}</div>
          )}

          {sourcesLoading ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="ow-skeleton h-56 rounded-xl" />
              ))}
            </div>
          ) : filteredSources.length === 0 ? (
            <EmptyState
              icon={Database}
              title="Nenhuma fonte encontrada"
              description="Tente ajustar os filtros de busca."
            />
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {filteredSources.map((item) => (
                <SourceCard key={item.connector} item={item} />
              ))}
            </div>
          )}
        </section>

        {/* ── Analytics section ────────────────────────────────── */}
        <section className="ow-card p-5">
          <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg shrink-0"
                style={{ background: "var(--color-surface-3)" }}>
                <Lightbulb className="h-4 w-4" style={{ color: "var(--color-text-3)" }} />
              </div>
              <p className="text-mono-xs uppercase tracking-widest" style={{ color: "var(--color-text-3)" }}>
                Cobertura Analítica por Tipologia
              </p>
            </div>
            {analytics && (
              <div className="flex gap-2 flex-wrap">
                <span className="ow-badge ow-badge-low">{analytics.summary.apt_count} aptas</span>
                <span className="ow-badge ow-badge-critical">{analytics.summary.blocked_count} bloqueadas</span>
                <span className="ow-badge ow-badge-amber">{analytics.summary.with_signals_30d} c/ sinais</span>
              </div>
            )}
          </div>

          {analyticsLoading ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 9 }).map((_, i) => (
                <div key={i} className="ow-skeleton h-40 rounded-xl" />
              ))}
            </div>
          ) : analytics ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {analytics.items.map((item) => (
                <TypologyCard key={item.typology_code} item={item} />
              ))}
            </div>
          ) : null}
        </section>

      </div>

      {/* ── Pipeline modal ───────────────────────────────────────── */}
      <PipelineModal open={pipelineModalOpen} onClose={() => setPipelineModalOpen(false)} />
    </div>
  );
}
