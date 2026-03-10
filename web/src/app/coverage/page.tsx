"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  getCoverageV2Analytics,
  getCoverageV2SourcePreview,
  getCoverageV2Sources,
  getCoverageV2Summary,
  getPipelineCapacity,
  getPipelineStatus,
  triggerFullPipeline,
  type PipelineCapacity,
  type PipelineDispatchResponse,
  type PipelineStatusResponse,
} from "@/lib/api";
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
  Search,
  X,
  XCircle,
  Zap,
} from "lucide-react";

// ── Status config ────────────────────────────────────────────────────────────

const STATUS_CFG: Record<CoverageStatus, { label: string; dot: string; text: string; border: string; bg: string }> = {
  ok:      { label: "OK",       dot: "bg-success",    text: "text-success",    border: "border-success/30",    bg: "bg-success/5"    },
  warning: { label: "Atenção",  dot: "bg-amber",       text: "text-amber",       border: "border-amber/30",       bg: "bg-amber/5"       },
  stale:   { label: "Defasado", dot: "bg-yellow-500",  text: "text-yellow-600",  border: "border-yellow-500/30",  bg: "bg-yellow-500/5"  },
  error:   { label: "Erro",     dot: "bg-error",       text: "text-error",       border: "border-error/30",       bg: "bg-error/5"       },
  pending: { label: "Pendente", dot: "bg-muted/60",    text: "text-muted",       border: "border-border",         bg: "bg-surface-base"  },
};

const RUN_STATUS_CFG: Record<string, { dot: string; text: string; label: string }> = {
  completed: { dot: "bg-success",    text: "text-success",    label: "Concluído"  },
  running:   { dot: "bg-accent",     text: "text-accent",     label: "Executando" },
  error:     { dot: "bg-red-500",    text: "text-red-400",    label: "Erro"       },
  failed:    { dot: "bg-error",      text: "text-error",      label: "Falhou"     },
  yielded:   { dot: "bg-amber",      text: "text-amber",      label: "Cedeu vez"  },
  stuck:     { dot: "bg-amber",      text: "text-amber",      label: "Travado"    },
  skipped:   { dot: "bg-muted/60",   text: "text-muted",      label: "Ignorado"   },
  pending:   { dot: "bg-muted/60",   text: "text-muted",      label: "Pendente"   },
};

function StatusBadge({ status }: { status: CoverageStatus }) {
  const cfg = STATUS_CFG[status] ?? STATUS_CFG.pending;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${cfg.border} ${cfg.bg} ${cfg.text}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}

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

// ── Run card ─────────────────────────────────────────────────────────────────

function RunCard({ run }: { run: CoverageV2LatestRun }) {
  const key = run.is_stuck ? "stuck" : run.status;
  const cfg = RUN_STATUS_CFG[key] ?? RUN_STATUS_CFG.pending;

  return (
    <div className="rounded-lg border border-border bg-surface-base p-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full ${cfg.dot}`} />
          <span className={`font-mono text-xs font-bold ${cfg.text}`}>
            {run.is_stuck ? "Travado" : (RUN_STATUS_CFG[run.status]?.label ?? run.status)}
          </span>
          <span className="font-mono text-[10px] text-muted">
            {formatDuration(run.started_at, run.finished_at)}
          </span>
        </div>
        <Link
          href={`/coverage/run/${run.id}`}
          className="flex items-center gap-1 font-mono text-[10px] text-accent hover:underline"
        >
          Detalhar
          <ArrowUpRight className="h-2.5 w-2.5" />
        </Link>
      </div>
      <div className="grid grid-cols-2 gap-2 text-[10px] text-muted">
        <div>
          <p className="font-mono text-[9px] uppercase tracking-wide mb-0.5">Início</p>
          <p className="text-primary font-mono">{fmtDate(run.started_at)}</p>
        </div>
        <div>
          <p className="font-mono text-[9px] uppercase tracking-wide mb-0.5">Fim</p>
          <p className="text-primary font-mono">{fmtDate(run.finished_at)}</p>
        </div>
      </div>
      {(run.items_fetched > 0 || run.items_normalized > 0) && (
        <div className="flex items-center gap-4 text-[10px]">
          <span className="flex items-center gap-1 text-muted">
            <Package className="h-3 w-3 shrink-0" />
            <span className="font-mono font-bold text-primary">{run.items_fetched.toLocaleString("pt-BR")}</span>
            <span>coletados</span>
          </span>
          <span className="flex items-center gap-1 text-muted">
            <CheckCircle2 className="h-3 w-3 shrink-0 text-success" />
            <span className="font-mono font-bold text-primary">{run.items_normalized.toLocaleString("pt-BR")}</span>
            <span>normalizados</span>
          </span>
        </div>
      )}
      {/* Progress bar for running jobs */}
      {run.status === "running" && (
        <div className="space-y-1 mt-2">
          {run.progress_pct != null && (
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1.5 rounded-full bg-surface-subtle overflow-hidden">
                <div
                  className="h-full rounded-full bg-accent transition-all duration-500"
                  style={{ width: `${Math.min(run.progress_pct, 100)}%` }}
                />
              </div>
              <span className="font-mono text-[10px] text-accent font-bold">{run.progress_pct}%</span>
            </div>
          )}
          {run.elapsed_seconds != null && (
            <p className="font-mono text-[10px] text-muted">Tempo decorrido: {formatElapsed(run.elapsed_seconds)}</p>
          )}
        </div>
      )}
      {run.error_message && (
        <div className="flex items-start gap-1.5 rounded border border-error/20 bg-error/5 px-2 py-1.5">
          <AlertTriangle className="h-3 w-3 shrink-0 text-error mt-0.5" />
          <p className="font-mono text-[10px] text-error leading-snug">{run.error_message}</p>
        </div>
      )}
    </div>
  );
}

// ── KPI Strip ────────────────────────────────────────────────────────────────

function KpiStrip({ summary, loading }: { summary: CoverageV2SummaryResponse | null; loading: boolean }) {
  if (loading) {
    return (
      <div className="grid grid-cols-4 gap-3 sm:grid-cols-8">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-16 rounded-lg border border-border bg-surface-card animate-pulse" />
        ))}
      </div>
    );
  }

  const t = summary?.totals;
  const sc = t?.status_counts;
  const rt = t?.runtime;

  const kpis = [
    { label: "Fontes",   value: t?.connectors ?? 0,                  sub: null,                            dot: null              },
    { label: "Jobs",     value: t?.jobs ?? 0,                         sub: `${t?.jobs_enabled ?? 0} ativos`, dot: null              },
    { label: "Sinais",   value: formatNumber(t?.signals_total ?? 0),  sub: null,                            dot: null              },
    { label: "OK",       value: sc?.ok ?? 0,                          sub: null,                            dot: "bg-success"      },
    { label: "Atenção",  value: sc?.warning ?? 0,                     sub: null,                            dot: "bg-amber"        },
    { label: "Defasado", value: sc?.stale ?? 0,                       sub: null,                            dot: "bg-yellow-500"   },
    { label: "Erro",     value: sc?.error ?? 0,                       sub: null,                            dot: "bg-error"        },
    { label: "Travados", value: rt?.failed_or_stuck ?? 0,             sub: null,                            dot: rt?.failed_or_stuck ? "bg-error" : "bg-muted/40" },
  ] as { label: string; value: number | string; sub: string | null; dot: string | null }[];

  return (
    <div className="grid grid-cols-4 gap-3 sm:grid-cols-8">
      {kpis.map((k) => (
        <div key={k.label} className="rounded-lg border border-border bg-surface-card px-3 py-3">
          {k.dot ? (
            <div className="flex items-center gap-1.5 mb-1">
              <span className={`h-1.5 w-1.5 rounded-full ${k.dot}`} />
              <p className="font-mono text-[9px] uppercase tracking-widest text-muted">{k.label}</p>
            </div>
          ) : (
            <p className="font-mono text-[9px] uppercase tracking-widest text-muted mb-1">{k.label}</p>
          )}
          <p className="font-mono text-lg font-bold tabular-nums text-primary leading-none">{k.value}</p>
          {k.sub && <p className="font-mono text-[10px] text-muted mt-1">{k.sub}</p>}
        </div>
      ))}
    </div>
  );
}

// ── Pipeline stages ──────────────────────────────────────────────────────────

const STAGE_STATUS: Record<string, { label: string; icon: React.ReactNode; ring: string; bg: string; text: string }> = {
  up_to_date: { label: "Atualizado",    icon: <CheckCircle2 className="h-5 w-5" />, ring: "border-success",    bg: "bg-success/10",     text: "text-success"  },
  stale:      { label: "Desatualizado", icon: <Clock className="h-5 w-5" />,        ring: "border-amber",      bg: "bg-amber/10",       text: "text-amber"    },
  processing: { label: "Processando",   icon: <Activity className="h-5 w-5" />,     ring: "border-accent",     bg: "bg-accent/10",      text: "text-accent"   },
  warning:    { label: "Atenção",       icon: <AlertTriangle className="h-5 w-5" />, ring: "border-amber",      bg: "bg-amber/10",       text: "text-amber"    },
  error:      { label: "Erro",          icon: <XCircle className="h-5 w-5" />,       ring: "border-error",      bg: "bg-error/10",       text: "text-error"    },
  pending:    { label: "Pendente",      icon: <Clock className="h-5 w-5" />,         ring: "border-border",     bg: "bg-surface-subtle", text: "text-muted"    },
};

const OVERALL_CFG: Record<string, { label: string; cls: string }> = {
  healthy:   { label: "Saudável",  cls: "text-success border-success/30 bg-success/5"  },
  attention: { label: "Atenção",   cls: "text-amber   border-amber/30   bg-amber/5"    },
  blocked:   { label: "Bloqueado", cls: "text-error   border-error/30   bg-error/5"    },
};

function PipelineStrip({ summary }: { summary: CoverageV2SummaryResponse | null }) {
  if (!summary) return null;
  const stages = summary.pipeline.stages;
  const ocfg = OVERALL_CFG[summary.pipeline.overall_status] ?? OVERALL_CFG.healthy;
  return (
    <div className="rounded-xl border border-border bg-surface-card p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted">Pipeline de Ingestão</p>
          <p className="text-sm font-semibold text-primary mt-0.5">Estado atual de cada etapa de processamento</p>
        </div>
        <span className={`rounded-full border px-3 py-1 text-[10px] font-bold uppercase tracking-wide ${ocfg.cls}`}>
          {ocfg.label}
        </span>
      </div>

      <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${stages.length}, minmax(0, 1fr))` }}>
        {stages.map((stage, i) => {
          const scfg = STAGE_STATUS[stage.status] ?? STAGE_STATUS.pending;
          const isProcessing = stage.status === "processing";
          return (
            <div key={stage.code} className="relative">
              {/* Connector line */}
              {i < stages.length - 1 && (
                <div className="absolute top-6 left-[calc(50%+1.5rem)] right-[-calc(50%-1.5rem)] h-px bg-border z-0" />
              )}
              <div className={`relative z-10 rounded-xl border-2 ${scfg.ring} ${scfg.bg} p-4 flex flex-col items-center gap-3 text-center overflow-hidden`}>
                {/* Animated scan line for processing stages */}
                {isProcessing && (
                  <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-transparent via-accent to-transparent animate-[slide_2s_linear_infinite]" />
                )}
                <div className={`flex h-12 w-12 items-center justify-center rounded-full bg-surface-card shadow-sm ${scfg.text}`}>
                  {scfg.icon}
                </div>
                <div>
                  <p className="font-display text-xs font-bold text-primary leading-snug">{stage.label}</p>
                  <p className={`font-mono text-[10px] font-bold uppercase mt-0.5 ${scfg.text}`}>{scfg.label}</p>
                  {stage.reason && stage.status !== "up_to_date" && (
                    <p className="text-[10px] text-secondary mt-1.5 leading-snug">{stage.reason}</p>
                  )}
                </div>
                {/* Indeterminate progress bar for processing stages */}
                {isProcessing && (
                  <div className="w-full h-1 rounded-full bg-surface-subtle overflow-hidden">
                    <div className="h-full w-1/3 rounded-full bg-accent animate-[progress_1.5s_ease-in-out_infinite]" />
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

// Overrides worst_status badge with an animated "Executando" pill when any job
// belonging to this source is actively running, so the user can see live activity.
function EffectiveBadge({ item }: { item: CoverageV2SourceItem }) {
  if (item.runtime.running_jobs > 0) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-accent/30 bg-accent/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-accent">
        <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
        Executando
      </span>
    );
  }
  return <StatusBadge status={item.worst_status} />;
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

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div className="relative z-10 flex w-full max-w-3xl max-h-[88vh] flex-col rounded-2xl border border-border bg-surface-card shadow-2xl overflow-hidden">

        {/* ── Modal header ────────────────────────────────── */}
        <div className={`flex items-start justify-between gap-4 border-b border-border px-6 py-4 ${cfg.bg}`}>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="font-display text-base font-bold text-primary capitalize">
                {item.connector_label}
              </h2>
              <EffectiveBadge item={item} />
            </div>
            <p className="font-mono text-[10px] text-muted mt-0.5">{item.connector}</p>
          </div>
          <button
            onClick={onClose}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-border bg-surface-base text-muted transition hover:bg-surface-subtle hover:text-primary"
            aria-label="Fechar diagnóstico"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* ── Summary strip ───────────────────────────────── */}
        <div className="grid grid-cols-4 gap-3 border-b border-border px-6 py-4">
          <div>
            <p className="font-mono text-[9px] uppercase tracking-widest text-muted mb-1">Jobs</p>
            <p className="font-mono text-lg font-bold text-primary leading-none">{item.job_count}</p>
            <p className="font-mono text-[10px] text-muted mt-0.5">{item.enabled_job_count} habilitados</p>
          </div>
          <div>
            <p className="font-mono text-[9px] uppercase tracking-widest text-muted mb-1">Em execução</p>
            <p className={`font-mono text-lg font-bold leading-none ${item.runtime.running_jobs > 0 ? "text-accent" : "text-primary"}`}>
              {item.runtime.running_jobs}
            </p>
          </div>
          <div>
            <p className="font-mono text-[9px] uppercase tracking-widest text-muted mb-1">Com erro</p>
            <p className={`font-mono text-lg font-bold leading-none ${item.runtime.error_jobs > 0 ? "text-error" : "text-primary"}`}>
              {item.runtime.error_jobs}
            </p>
          </div>
          <div>
            <p className="font-mono text-[9px] uppercase tracking-widest text-muted mb-1">Defasagem</p>
            <p className={`font-mono text-lg font-bold leading-none ${
              item.max_freshness_lag_hours == null ? "text-muted" :
              item.max_freshness_lag_hours > 48 ? "text-error" :
              item.max_freshness_lag_hours > 24 ? "text-amber" : "text-success"
            }`}>
              {formatLag(item.max_freshness_lag_hours)}
            </p>
            {item.last_success_at && (
              <p className="font-mono text-[9px] text-muted mt-0.5">
                {new Date(item.last_success_at).toLocaleString("pt-BR")}
              </p>
            )}
          </div>
        </div>

        {/* ── Scrollable body ─────────────────────────────── */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6 bg-surface-base">

          {loading && (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-20 rounded-xl border border-border animate-pulse" />
              ))}
            </div>
          )}

          {error && (
            <div className="flex items-start gap-2 rounded-xl border border-error/20 bg-error/5 p-4 text-sm text-error">
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
              {error}
            </div>
          )}

          {preview && (
            <>
              {/* Stuck warning */}
              {item.runtime.stuck_jobs > 0 && (
                <div className="flex items-center gap-2 rounded-xl border border-error/20 bg-error/5 px-4 py-3 text-sm text-error">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  {item.runtime.stuck_jobs} job(s) travado(s) — restart recomendado
                </div>
              )}

              {/* Insights */}
              {preview.insights.length > 0 && (
                <section>
                  <p className="font-mono text-[9px] uppercase tracking-widest text-muted mb-3">
                    Insights ({preview.insights.length})
                  </p>
                  <div className="space-y-2">
                    {preview.insights.map((insight, i) => (
                      <div key={i} className="flex items-start gap-3 rounded-xl border border-accent/20 bg-accent-subtle/30 px-4 py-3">
                        <Lightbulb className="h-4 w-4 shrink-0 text-accent mt-0.5" />
                        <p className="text-sm text-secondary leading-relaxed">{insight}</p>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Jobs */}
              <section>
                <p className="font-mono text-[9px] uppercase tracking-widest text-muted mb-3">
                  Jobs ({preview.jobs.length})
                </p>
                <div className="space-y-4">
                  {preview.jobs.map((job) => {
                    const isJobRunning = job.latest_run?.status === "running";
                    const scfg = STATUS_CFG[job.status] ?? STATUS_CFG.pending;
                    return (
                      <div key={job.job} className={`rounded-xl border ${isJobRunning ? "border-accent/30 bg-accent/5" : scfg.border + " bg-surface-card"} p-4 space-y-4`}>
                        {/* Job header */}
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="flex items-center gap-2 flex-wrap mb-1">
                              <span className="font-mono text-sm font-bold text-primary">{job.job}</span>
                              {!job.enabled_in_mvp && (
                                <span className="rounded-full border border-border bg-surface-subtle px-1.5 py-0.5 text-[9px] font-bold uppercase text-muted">
                                  Desabilitado
                                </span>
                              )}
                            </div>
                            <p className="font-mono text-xs text-accent">{job.domain}</p>
                            {job.description && (
                              <p className="text-xs text-secondary mt-1 leading-relaxed">{job.description}</p>
                            )}
                          </div>
                          {isJobRunning ? (
                            <span className="inline-flex items-center gap-1.5 rounded-full border border-accent/30 bg-accent/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-accent">
                              <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
                              Executando
                            </span>
                          ) : (
                            <StatusBadge status={job.status} />
                          )}
                        </div>

                        {/* Job metrics */}
                        <div className="grid grid-cols-3 gap-3">
                          <div className="rounded-lg border border-border bg-surface-base px-3 py-2">
                            <p className="font-mono text-[9px] uppercase tracking-wide text-muted mb-0.5">Itens totais</p>
                            <p className="font-mono text-sm font-bold text-primary">{job.total_items.toLocaleString("pt-BR")}</p>
                          </div>
                          <div className="rounded-lg border border-border bg-surface-base px-3 py-2">
                            <p className="font-mono text-[9px] uppercase tracking-wide text-muted mb-0.5">Defasagem</p>
                            <p className={`font-mono text-sm font-bold ${
                              job.freshness_lag_hours == null ? "text-muted" :
                              job.freshness_lag_hours > 48 ? "text-error" :
                              job.freshness_lag_hours > 24 ? "text-amber" : "text-success"
                            }`}>
                              {formatLag(job.freshness_lag_hours)}
                            </p>
                          </div>
                          <div className="rounded-lg border border-border bg-surface-base px-3 py-2">
                            <p className="font-mono text-[9px] uppercase tracking-wide text-muted mb-0.5">Último sucesso</p>
                            <p className="font-mono text-xs text-primary">
                              {job.last_success_at ? fmtDate(job.last_success_at) : "Não registrado"}
                            </p>
                          </div>
                        </div>

                        {/* Pipeline progress strip — visible without clicking Detalhar */}
                        {job.latest_run && (
                          <JobPipelineStrip run={job.latest_run} />
                        )}

                        {/* Latest run */}
                        {job.latest_run && (
                          <div>
                            <p className="font-mono text-[9px] uppercase tracking-wide text-muted mb-2">Execução mais recente</p>
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

        {/* ── Modal footer ────────────────────────────────── */}
        <div className="flex items-center justify-between border-t border-border px-6 py-3 bg-surface-card">
          <p className="font-mono text-[10px] text-muted">
            Último sucesso:{" "}
            <span className="text-primary">
              {item.last_success_at ? new Date(item.last_success_at).toLocaleString("pt-BR") : "—"}
            </span>
          </p>
          <button
            onClick={onClose}
            className="rounded-lg border border-border bg-surface-base px-4 py-1.5 text-xs font-semibold text-secondary transition hover:bg-surface-subtle hover:text-primary"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Job pipeline strip ────────────────────────────────────────────────────────
// Shows ingest→normalize progress per job (ER and signals are global, shown at page level).

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

  return (
    <div className="rounded-lg border border-border bg-surface-base px-3 py-2.5 space-y-2">
      <div className="flex items-center justify-between">
        <p className="font-mono text-[9px] uppercase tracking-widest text-muted">
          Pipeline de Processamento
        </p>
        {isRunning && startMs > 0 && (
          <span className="font-mono text-[10px] text-accent">{elapsedStr} em execução</span>
        )}
      </div>
      <div className="flex items-stretch gap-0.5">
        {stages.map((stage) => (
          <div
            key={stage.key}
            className={`flex-1 rounded border px-2 py-1.5 min-w-0 ${
              stage.status === "error"
                ? "border-red-500/30 bg-red-500/5"
                : stage.status === "blocked"
                ? "border-border bg-surface-subtle opacity-50"
                : stage.status === "active"
                ? "border-accent/40 bg-accent/10"
                : stage.status === "done"
                ? "border-success/30 bg-success/5"
                : "border-border bg-surface-subtle"
            }`}
          >
            <div className="flex items-center gap-1 mb-0.5">
              {stage.status === "error" && (
                <span className="h-1.5 w-1.5 rounded-full bg-red-500 shrink-0" />
              )}
              {stage.status === "active" && (
                <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse shrink-0" />
              )}
              {stage.status === "done" && (
                <span className="h-1.5 w-1.5 rounded-full bg-success shrink-0" />
              )}
              <p
                className={`font-mono text-[9px] font-bold uppercase truncate ${
                  stage.status === "error"
                    ? "text-red-400"
                    : stage.status === "active"
                    ? "text-accent"
                    : stage.status === "done"
                    ? "text-success"
                    : "text-muted"
                }`}
              >
                {stage.label}
              </p>
            </div>
            {stage.line1 && (
              <p
                className={`font-mono text-[9px] leading-tight truncate ${
                  stage.status === "error"
                    ? "text-red-400/80"
                    : stage.status === "active"
                    ? "text-accent/80"
                    : stage.status === "done"
                    ? "text-success/80"
                    : "text-muted/60"
                }`}
              >
                {stage.line1}
              </p>
            )}
            {stage.line2 && (
              <p className="font-mono text-[9px] text-muted leading-tight">{stage.line2}</p>
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

  function handleOpenModal() {
    setModalOpen(true);
    if (preview === null && !previewLoading) {
      setPreviewLoading(true);
      setPreviewError(null);
      getCoverageV2SourcePreview(item.connector, { runs_limit: 5 })
        .then(setPreview)
        .catch(() => setPreviewError("Não foi possível carregar o diagnóstico."))
        .finally(() => setPreviewLoading(false));
    }
  }

  // Bar always spans 100% width: colored segments for meaningful states,
  // faded trailing segment for pending (unfilled but visible as a track).
  const statusBar = [
    { key: "ok"      as CoverageStatus, count: item.status_counts.ok,      color: "bg-success"    },
    { key: "warning" as CoverageStatus, count: item.status_counts.warning,  color: "bg-amber"      },
    { key: "stale"   as CoverageStatus, count: item.status_counts.stale,    color: "bg-yellow-500" },
    { key: "error"   as CoverageStatus, count: item.status_counts.error,    color: "bg-error"      },
    { key: "pending" as CoverageStatus, count: item.status_counts.pending,  color: "bg-muted/25"   },
  ].filter((s) => s.count > 0);

  // Legend reuses statusBar (already includes pending); override pending dot to a slightly brighter shade.
  const statusLegend = statusBar.map((s) =>
    s.key === "pending" ? { ...s, color: "bg-muted/60" } : s
  );

  return (
    <div className={`relative rounded-xl border ${item.runtime.running_jobs > 0 ? "border-accent/50" : cfg.border} bg-surface-card flex flex-col`}>
      {/* Pulse ring for running connectors */}
      {item.runtime.running_jobs > 0 && (
        <span className="pointer-events-none absolute inset-0 rounded-xl ring-2 ring-accent/40 animate-pulse" />
      )}
      {/* ── Card summary ─────────────────────────────────────── */}
      <div className="flex flex-col gap-4 p-4 flex-1">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="font-display text-sm font-bold text-primary capitalize leading-snug">
              {item.connector_label}
            </h3>
            <p className="font-mono text-[10px] text-muted mt-0.5">{item.connector}</p>
          </div>
          <EffectiveBadge item={item} />
        </div>

        {/* Counts row */}
        <div className="flex flex-wrap items-center gap-3 text-xs text-muted">
          <span className="flex items-center gap-1">
            <FileText className="h-3 w-3 shrink-0" />
            <span className="font-mono font-bold text-primary">{item.job_count}</span>
            <span>jobs</span>
          </span>
          <span className="flex items-center gap-1 text-accent">
            <Zap className="h-3 w-3 shrink-0" />
            <span className="font-mono font-bold">{item.enabled_job_count}</span>
            <span>habilitados</span>
          </span>
          {item.runtime.running_jobs > 0 && (
            <span className="flex items-center gap-1 text-accent">
              <Activity className="h-3 w-3 shrink-0" />
              {item.runtime.running_jobs} em exec.
            </span>
          )}
          {item.runtime.error_jobs > 0 && (
            <span className="flex items-center gap-1 text-error">
              <AlertTriangle className="h-3 w-3 shrink-0" />
              {item.runtime.error_jobs} com erro
            </span>
          )}
        </div>

        {/* Status distribution */}
        {totalJobs > 0 && (
          <div className="space-y-1.5">
            <div className="flex h-2 rounded-full overflow-hidden gap-px">
              {statusBar.map((s) => (
                <div
                  key={s.key}
                  className={s.color}
                  style={{ width: `${(s.count / totalJobs) * 100}%` }}
                  title={`${STATUS_CFG[s.key]?.label}: ${s.count}`}
                />
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              {statusLegend.map((s) => (
                <span key={s.key} className="flex items-center gap-1 text-[10px] text-muted">
                  <span className={`h-1.5 w-1.5 rounded-full ${s.color}`} />
                  {STATUS_CFG[s.key]?.label}: <span className="font-mono font-bold text-primary">{s.count}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Live progress when running */}
        {item.runtime.running_jobs > 0 && (
          <div className="rounded-lg border border-accent/20 bg-accent/5 px-3 py-2.5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-accent">
                <Loader2 className="h-3 w-3 animate-spin" />
                Executando {item.runtime.running_jobs} job(s)
              </span>
              {item.runtime.elapsed_seconds != null && (
                <span className="font-mono text-[10px] text-muted">
                  {formatElapsed(item.runtime.elapsed_seconds)}
                </span>
              )}
            </div>
            {item.runtime.active_job_names?.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {item.runtime.active_job_names.map((name) => (
                  <span key={name} className="rounded-full bg-accent/10 border border-accent/20 px-2 py-0.5 font-mono text-[9px] text-accent">
                    {name}
                  </span>
                ))}
              </div>
            )}
            <div className="flex items-center gap-4 text-[10px] text-secondary">
              {item.runtime.items_fetched_live > 0 && (
                <span className="font-mono">
                  {item.runtime.items_fetched_live.toLocaleString("pt-BR")} itens coletados
                </span>
              )}
              {item.runtime.items_normalized_live > 0 && (
                <span className="font-mono">
                  {item.runtime.items_normalized_live.toLocaleString("pt-BR")} normalizados
                </span>
              )}
              {item.runtime.estimated_rate_per_min != null && item.runtime.estimated_rate_per_min > 0 && (
                <span className="font-mono text-accent">
                  ~{item.runtime.estimated_rate_per_min.toLocaleString("pt-BR")}/min
                </span>
              )}
            </div>
          </div>
        )}

        {/* Freshness */}
        <div className="rounded-lg border border-border bg-surface-base px-3 py-2 space-y-1">
          <div className="flex items-center justify-between text-[10px] text-muted">
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Último sucesso
            </span>
            {item.max_freshness_lag_hours != null && (
              <span className={`font-mono font-bold ${item.max_freshness_lag_hours > 48 ? "text-error" : item.max_freshness_lag_hours > 24 ? "text-amber" : "text-success"}`}>
                {formatLag(item.max_freshness_lag_hours)} defasagem
              </span>
            )}
          </div>
          <p className="font-mono text-xs text-primary">
            {item.last_success_at
              ? new Date(item.last_success_at).toLocaleString("pt-BR")
              : "Sem execução registrada"}
          </p>
        </div>

        {/* Stuck warning */}
        {item.runtime.stuck_jobs > 0 && (
          <div className="flex items-center gap-2 rounded-lg border border-error/20 bg-error/5 px-3 py-2 text-xs text-error">
            <AlertTriangle className="h-3 w-3 shrink-0" />
            {item.runtime.stuck_jobs} job(s) travado(s) — restart recomendado
          </div>
        )}
      </div>

      {/* ── Modal trigger ─────────────────────────────────────── */}
      <button
        onClick={handleOpenModal}
        className="flex w-full items-center justify-center gap-1.5 border-t border-border px-4 py-2.5 text-[11px] font-semibold text-muted transition hover:bg-surface-subtle hover:text-primary"
      >
        <FileText className="h-3.5 w-3.5" />
        Ver diagnóstico detalhado
      </button>

      {/* ── Diagnostic modal ──────────────────────────────────── */}
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

// ── Typology info modal ────────────────────────────────────────────────────────

function TypologyInfoModal({
  item,
  onClose,
}: {
  item: AnalyticalCoverageItem;
  onClose: () => void;
}) {
  const domainTotal = item.required_domains.length;
  const domainAvail = item.domains_available.length;
  const pct = domainTotal > 0 ? Math.round((domainAvail / domainTotal) * 100) : 0;
  const barColor = item.apt ? "bg-success" : pct > 0 ? "bg-amber" : "bg-error";

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div className="relative z-10 flex w-full max-w-2xl max-h-[88vh] flex-col rounded-2xl border border-border bg-surface-card shadow-2xl overflow-hidden">

        {/* ── Header ──────────────────────────────────────────── */}
        <div className="flex items-start justify-between gap-4 border-b border-border px-6 py-4">
          <div>
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <span className="font-mono text-xs font-bold text-accent">{item.typology_code}</span>
              {item.apt ? (
                <span className="rounded-full border border-success/30 bg-success/5 px-1.5 py-0.5 text-[9px] font-bold uppercase text-success">
                  Apta
                </span>
              ) : (
                <span className="rounded-full border border-error/30 bg-error/5 px-1.5 py-0.5 text-[9px] font-bold uppercase text-error">
                  Bloqueada
                </span>
              )}
            </div>
            <h2 className="font-display text-base font-bold text-primary">{item.typology_name}</h2>
          </div>
          <button
            onClick={onClose}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-border bg-surface-base text-muted transition hover:bg-surface-subtle hover:text-primary"
            aria-label="Fechar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* ── Summary strip ───────────────────────────────────── */}
        <div className="grid grid-cols-3 gap-3 border-b border-border px-6 py-4">
          <div>
            <p className="font-mono text-[9px] uppercase tracking-widest text-muted mb-1">Evidência</p>
            <p className="font-mono text-sm font-bold text-primary capitalize">{item.evidence_level ?? "—"}</p>
          </div>
          <div>
            <p className="font-mono text-[9px] uppercase tracking-widest text-muted mb-1">Domínios</p>
            <p className="font-mono text-sm font-bold text-primary">{domainAvail}/{domainTotal}</p>
            <p className="font-mono text-[10px] text-muted">{pct}% coberto</p>
          </div>
          <div>
            <p className="font-mono text-[9px] uppercase tracking-widest text-muted mb-1">Sinais 30d</p>
            <p className={`font-mono text-sm font-bold ${item.signals_30d > 0 ? "text-success" : "text-muted"}`}>
              {item.signals_30d}
            </p>
          </div>
        </div>

        {/* ── Scrollable body ─────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6 bg-surface-base">

          {/* Description legal */}
          {item.description_legal && (
            <section>
              <p className="font-mono text-[9px] uppercase tracking-widest text-muted mb-3">Descrição Legal</p>
              <div className="flex items-start gap-3 rounded-xl border border-accent/20 bg-accent-subtle/30 px-4 py-3">
                <Lightbulb className="h-4 w-4 shrink-0 text-accent mt-0.5" />
                <p className="text-sm text-secondary leading-relaxed">{item.description_legal}</p>
              </div>
            </section>
          )}

          {/* Domains */}
          <section>
            <p className="font-mono text-[9px] uppercase tracking-widest text-muted mb-3">Domínios de Dados Necessários</p>
            <div className="rounded-xl border border-border bg-surface-card p-4 space-y-3">
              <div className="h-1.5 rounded-full bg-surface-subtle overflow-hidden">
                <div className={`h-full ${barColor} transition-all`} style={{ width: `${pct}%` }} />
              </div>
              <div className="flex flex-wrap gap-2">
                {item.domains_available.map((d) => (
                  <span key={d} className="flex items-center gap-1 rounded-full border border-success/20 bg-success/5 px-2 py-0.5 text-[10px] font-medium text-success">
                    <CheckCircle2 className="h-3 w-3" />
                    {d}
                  </span>
                ))}
                {item.domains_missing.map((d) => (
                  <span key={d} className="flex items-center gap-1 rounded-full border border-error/20 bg-error/5 px-2 py-0.5 text-[10px] font-medium text-error">
                    <XCircle className="h-3 w-3" />
                    {d}
                  </span>
                ))}
              </div>
              {item.domains_missing.length > 0 && (
                <p className="text-xs text-muted leading-relaxed">
                  {item.domains_missing.length === 1
                    ? "1 domínio ausente — a tipologia permanece bloqueada até que todos os domínios necessários estejam disponíveis."
                    : `${item.domains_missing.length} domínios ausentes — a tipologia permanece bloqueada até que todos os domínios necessários estejam disponíveis.`}
                </p>
              )}
            </div>
          </section>

          {/* Classification */}
          {((item.corruption_types && item.corruption_types.length > 0) || (item.spheres && item.spheres.length > 0)) && (
            <section>
              <p className="font-mono text-[9px] uppercase tracking-widest text-muted mb-3">Classificação Jurídica</p>
              <div className="rounded-xl border border-border bg-surface-card p-4 space-y-4">
                {item.corruption_types && item.corruption_types.length > 0 && (
                  <div>
                    <p className="font-mono text-[10px] text-muted mb-2">Tipos de corrupção cobertos</p>
                    <div className="flex flex-wrap gap-1.5">
                      {item.corruption_types.map((ct) => (
                        <span key={ct} className="rounded-full border border-border bg-surface-base px-2 py-0.5 text-[10px] font-medium text-secondary capitalize">
                          {ct.replace(/_/g, " ")}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {item.spheres && item.spheres.length > 0 && (
                  <div>
                    <p className="font-mono text-[10px] text-muted mb-2">Esferas</p>
                    <div className="flex flex-wrap gap-1.5">
                      {item.spheres.map((s) => (
                        <span key={s} className="rounded-full border border-accent/20 bg-accent/5 px-2 py-0.5 text-[10px] font-medium text-accent capitalize">
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Last run */}
          {item.last_run_at && (
            <section>
              <p className="font-mono text-[9px] uppercase tracking-widest text-muted mb-3">Última Execução</p>
              <div className="rounded-xl border border-border bg-surface-card p-4 grid grid-cols-2 gap-3">
                <div>
                  <p className="font-mono text-[9px] text-muted mb-0.5">Data</p>
                  <p className="font-mono text-xs text-primary">{new Date(item.last_run_at).toLocaleString("pt-BR")}</p>
                </div>
                {item.last_run_status && (
                  <div>
                    <p className="font-mono text-[9px] text-muted mb-0.5">Status</p>
                    <p className={`font-mono text-xs font-bold ${item.last_run_status === "success" ? "text-success" : item.last_run_status === "running" ? "text-accent" : "text-error"}`}>
                      {item.last_run_status}
                    </p>
                  </div>
                )}
                {item.last_run_candidates != null && item.last_run_candidates > 0 && (
                  <div>
                    <p className="font-mono text-[9px] text-muted mb-0.5">Candidatos</p>
                    <p className="font-mono text-xs font-bold text-primary">{item.last_run_candidates}</p>
                  </div>
                )}
                {item.last_run_signals_created != null && (
                  <div>
                    <p className="font-mono text-[9px] text-muted mb-0.5">Sinais criados</p>
                    <p className="font-mono text-xs font-bold text-primary">{item.last_run_signals_created}</p>
                  </div>
                )}
              </div>
            </section>
          )}
        </div>

        {/* ── Footer ──────────────────────────────────────────── */}
        <div className="flex items-center justify-end border-t border-border px-6 py-3 bg-surface-card">
          <button
            onClick={onClose}
            className="rounded-lg border border-border bg-surface-base px-4 py-1.5 text-xs font-semibold text-secondary transition hover:bg-surface-subtle hover:text-primary"
          >
            Fechar
          </button>
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
  const barColor = item.apt ? "bg-success" : pct > 0 ? "bg-amber" : "bg-error";
  const borderColor = item.apt ? "border-success/20" : pct > 0 ? "border-amber/20" : "border-error/20";

  return (
    <div className={`rounded-xl border ${borderColor} bg-surface-card flex flex-col`}>
      <div className="p-4 space-y-3 flex-1">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="font-mono text-xs font-bold text-accent shrink-0">{item.typology_code}</span>
            {item.apt ? (
              item.signals_30d > 0 ? (
                <span className="rounded-full border border-success/30 bg-success/5 px-1.5 py-0.5 text-[9px] font-bold uppercase text-success">
                  Ativa · {item.signals_30d} sinais/30d
                </span>
              ) : (
                <span className="rounded-full border border-success/30 bg-success/5 px-1.5 py-0.5 text-[9px] font-bold uppercase text-success">
                  Apta
                </span>
              )
            ) : (
              <span className="rounded-full border border-error/30 bg-error/5 px-1.5 py-0.5 text-[9px] font-bold uppercase text-error">
                Bloqueada
              </span>
            )}
          </div>
          <p className="text-xs font-semibold text-primary leading-snug">{item.typology_name}</p>
        </div>
        <span className="font-mono text-sm font-bold text-primary shrink-0">{pct}%</span>
      </div>

      <div>
        <div className="flex items-center justify-between mb-1">
          <p className="font-mono text-[10px] text-muted">Domínios cobertos</p>
          <p className="font-mono text-[10px] text-muted">{domainAvail}/{domainTotal}</p>
        </div>
        <div className="h-1.5 rounded-full bg-surface-subtle overflow-hidden">
          <div className={`h-full ${barColor} transition-all`} style={{ width: `${pct}%` }} />
        </div>
      </div>

      {(item.domains_available.length > 0 || item.domains_missing.length > 0) && (
        <div className="flex flex-wrap gap-1">
          {item.domains_available.map((d) => (
            <span key={d} className="rounded-full border border-success/20 bg-success/5 px-1.5 py-0.5 text-[10px] font-medium text-success">
              {d}
            </span>
          ))}
          {item.domains_missing.map((d) => (
            <span key={d} className="rounded-full border border-error/20 bg-error/5 px-1.5 py-0.5 text-[10px] font-medium text-error line-through opacity-70">
              {d}
            </span>
          ))}
        </div>
      )}


      {(item.last_run_at || item.last_run_candidates != null || item.signals_30d > 0) && (
        <div className="grid grid-cols-2 gap-x-3 gap-y-1 border-t border-border pt-2">
          {item.signals_30d > 0 && (
            <div className="text-[10px]">
              <span className="text-muted">Sinais 30d: </span>
              <span className="font-mono font-bold text-primary">{item.signals_30d}</span>
            </div>
          )}
          {item.last_run_candidates != null && item.last_run_candidates > 0 && (
            <div className="text-[10px]">
              <span className="text-muted">Candidatos: </span>
              <span className="font-mono font-bold text-primary">{item.last_run_candidates}</span>
            </div>
          )}
          {item.last_run_signals_created != null && (
            <div className="text-[10px]">
              <span className="text-muted">Criados: </span>
              <span className="font-mono font-bold text-primary">{item.last_run_signals_created}</span>
            </div>
          )}
          {item.last_run_signals_deduped != null && item.last_run_signals_deduped > 0 && (
            <div className="text-[10px]">
              <span className="text-muted">Deduped: </span>
              <span className="font-mono font-bold text-primary">{item.last_run_signals_deduped}</span>
            </div>
          )}
          {item.last_run_at && (
            <div className="col-span-2 text-[10px]">
              <span className="text-muted">Última exec.: </span>
              <span className="font-mono text-primary">
                {new Date(item.last_run_at).toLocaleString("pt-BR")}
              </span>
              {item.last_run_status && (
                <span className={`ml-1.5 font-mono font-bold ${item.last_run_status === "success" ? "text-success" : item.last_run_status === "running" ? "text-accent" : "text-error"}`}>
                  · {item.last_run_status}
                </span>
              )}
            </div>
          )}
        </div>
      )}

      {(item.evidence_level || (item.corruption_types && item.corruption_types.length > 0)) && (
        <div className="flex flex-wrap gap-1 border-t border-border pt-2">
          {item.evidence_level && (
            <span className="rounded-full border border-border bg-surface-base px-1.5 py-0.5 text-[10px] font-medium text-muted capitalize">
              {item.evidence_level}
            </span>
          )}
          {item.corruption_types?.slice(0, 2).map((ct) => (
            <span key={ct} className="rounded-full border border-border bg-surface-base px-1.5 py-0.5 text-[10px] font-medium text-muted">
              {ct}
            </span>
          ))}
        </div>
      )}
      </div>

      <button
        onClick={() => setModalOpen(true)}
        className="flex w-full items-center justify-center gap-1.5 border-t border-border px-4 py-2.5 text-[11px] font-semibold text-muted transition hover:bg-surface-subtle hover:text-primary"
      >
        <BookOpen className="h-3.5 w-3.5" />
        Ver detalhes da tipologia
      </button>

      {modalOpen && (
        <TypologyInfoModal item={item} onClose={() => setModalOpen(false)} />
      )}
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
    description: "Execução das 18 tipologias de corrupção detectadas",
    worker: "worker-cpu",
  },
];

function PipelineModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
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

  // Check pipeline status every time the modal opens
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
      // 409 = already running (race between status check and button click)
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
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={!running ? resetAndClose : undefined} />
      <div className="relative w-full max-w-md rounded-2xl border border-border bg-surface-card shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-subtle border border-accent/20">
              <Zap className="h-4 w-4 text-accent" />
            </div>
            <div>
              <p className="font-semibold text-sm text-primary">Executar Pipeline</p>
              <p className="text-xs text-muted">Ingestão → ER → Sinais de Risco</p>
            </div>
          </div>
          <button
            onClick={resetAndClose}
            className="rounded-lg p-1.5 text-muted hover:bg-surface-base hover:text-primary transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Already running banner */}
        {alreadyRunning && (
          <div className="mx-6 mt-5 flex items-start gap-2.5 rounded-xl border border-amber/30 bg-amber/5 px-4 py-3">
            <Activity className="h-4 w-4 shrink-0 text-amber mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-amber">Pipeline já em execução</p>
              <p className="mt-0.5 text-xs text-secondary">Os workers já estão processando dados. Não é necessário executar novamente — aguarde a conclusão do ciclo atual.</p>
            </div>
          </div>
        )}

        {/* Checking state */}
        {checking && (
          <div className="flex items-center justify-center gap-2 py-6 text-xs text-muted">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Verificando estado do pipeline...
          </div>
        )}

        {/* Stages */}
        {!checking && (
          <div className="px-6 py-5 space-y-3">
            {PIPELINE_STAGE_DEFS.map((def, i) => {
              const stage = stages[def.key];
              const isActive = alreadyRunning && stage.status === "dispatched";
              const isDispatched = !alreadyRunning && stage.status === "dispatched";
              const isDispatching = stage.status === "dispatching";
              const isError = stage.status === "error";

              return (
                <div
                  key={def.key}
                  className={[
                    "flex items-start gap-3 rounded-xl border p-3.5 transition-all duration-300",
                    isActive ? "border-amber/30 bg-amber/5" :
                    isDispatched ? "border-success/30 bg-success/5" :
                    isError ? "border-error/20 bg-error/5" :
                    "border-border bg-surface-base",
                  ].join(" ")}
                >
                  <div className={[
                    "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold transition-all duration-300",
                    isActive ? "bg-amber/20 border border-amber/40" :
                    isDispatched ? "bg-success text-white" :
                    isError ? "bg-error text-white" :
                    "bg-surface-card border border-border text-muted",
                  ].join(" ")}>
                    {isDispatching ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-accent" />
                    ) : isActive ? (
                      <Activity className="h-3.5 w-3.5 text-amber" />
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
                      <p className={[
                        "text-sm font-semibold",
                        isActive ? "text-amber" :
                        isDispatched ? "text-success" :
                        isError ? "text-error" :
                        "text-primary",
                      ].join(" ")}>
                        {def.label}
                        {isActive && <span className="ml-2 text-[10px] font-normal text-amber/70">em execução</span>}
                      </p>
                      <span className="font-mono text-[10px] text-muted bg-surface-card border border-border rounded px-1.5 py-0.5 shrink-0">
                        {def.worker}
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs text-secondary">{def.description}</p>
                    {isDispatched && stage.taskId && (
                      <p className="mt-1.5 font-mono text-[10px] text-success/70 truncate">
                        task: {stage.taskId}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mx-6 mb-4 rounded-lg border border-error/20 bg-error/5 px-3 py-2 text-xs text-error">
            {error}
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t border-border px-6 py-4">
          {alreadyRunning ? (
            <div className="flex w-full items-center justify-between">
              <p className="flex items-center gap-1.5 text-xs text-secondary">
                <Clock className="h-3.5 w-3.5" />
                O pipeline conclui automaticamente
              </p>
              <button
                onClick={resetAndClose}
                className="rounded-lg border border-border bg-surface-base px-4 py-2 text-xs font-semibold text-primary hover:bg-surface-card transition-colors"
              >
                Fechar
              </button>
            </div>
          ) : allDispatched ? (
            <div className="flex w-full items-center justify-between">
              <p className="flex items-center gap-1.5 text-xs font-semibold text-success">
                <CheckCircle2 className="h-4 w-4" />
                Pipeline iniciado com sucesso
              </p>
              <button
                onClick={resetAndClose}
                className="rounded-lg border border-border bg-surface-base px-4 py-2 text-xs font-semibold text-primary hover:bg-surface-card transition-colors"
              >
                Fechar
              </button>
            </div>
          ) : (
            <>
              <button
                onClick={resetAndClose}
                disabled={running}
                className="rounded-lg border border-border bg-surface-base px-4 py-2 text-xs font-semibold text-primary hover:bg-surface-card disabled:opacity-40 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleExecute}
                disabled={running || checking}
                className="inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50 transition-opacity"
              >
                {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                {running ? "Iniciando..." : "Executar"}
              </button>
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

  useEffect(() => {
    let active = true;
    setSummaryLoading(true);
    getCoverageV2Summary()
      .then((d) => { if (active) setSummary(d); })
      .catch(() => { if (active) setSummaryError("Não foi possível carregar o resumo da cobertura."); })
      .finally(() => { if (active) setSummaryLoading(false); });
    return () => { active = false; };
  }, []);

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
    const interval = setInterval(fetchSources, 15_000);
    return () => { active = false; clearInterval(interval); };
  }, [enabledOnly]);

  useEffect(() => {
    let active = true;
    getCoverageV2Analytics()
      .then((d) => { if (active) setAnalytics(d); })
      .catch(() => {})
      .finally(() => { if (active) setAnalyticsLoading(false); });
    return () => { active = false; };
  }, []);

  // Capacity polling every 10s
  useEffect(() => {
    let active = true;
    const load = () => getPipelineCapacity().then((c) => { if (active) setCapacity(c); }).catch(() => {});
    load();
    const interval = setInterval(load, 10_000);
    return () => { active = false; clearInterval(interval); };
  }, []);

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
        // Running jobs always float to top
        const aRunning = a.runtime.running_jobs > 0 ? 0 : 1;
        const bRunning = b.runtime.running_jobs > 0 ? 0 : 1;
        if (aRunning !== bRunning) return aRunning - bRunning;
        const order: CoverageStatus[] = ["error", "warning", "stale", "ok", "pending"];
        return order.indexOf(a.worst_status) - order.indexOf(b.worst_status);
      });
  }, [sources, search, statusFilter]);

  return (
    <>
    <PipelineModal open={pipelineModalOpen} onClose={() => setPipelineModalOpen(false)} />
    <div className="min-h-screen">

      {/* ── Page header ─────────────────────────────────────────── */}
      <div className="border-b border-border bg-surface-card">
        <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-accent-subtle border border-accent/20">
                <Database className="h-6 w-6 text-accent" />
              </div>
              <div>
                <h1 className="font-display text-2xl font-bold tracking-tight text-primary sm:text-3xl">Cobertura de Dados</h1>
                <p className="mt-1.5 text-sm text-secondary leading-relaxed">Estado operacional do pipeline de ingestão e qualidade das fontes públicas federais</p>
              </div>
            </div>
            <div className="flex items-center gap-3 shrink-0 flex-wrap justify-end">
              {/* Capacity warning (maxed out — derived from capacity API or sources fallback) */}
              {(() => {
                const runningJobs = capacity?.running_ingest_jobs ?? sources.reduce((n, s) => n + s.runtime.running_jobs, 0);
                const maxJobs = capacity?.max_concurrent_ingest ?? 4;
                return !sourcesLoading && runningJobs >= maxJobs;
              })() && (
                <span className="group relative flex items-center gap-1.5 rounded-full border border-amber/30 bg-amber/5 px-3 py-1 text-xs text-amber cursor-help">
                  <AlertTriangle className="h-3 w-3" />
                  Capacidade máxima
                  {/* Hover tooltip */}
                  <div className="pointer-events-none absolute right-0 top-full z-50 mt-2 hidden w-72 rounded-lg border border-border bg-surface-card p-3 text-left shadow-lg group-hover:block">
                    <p className="mb-2 text-xs font-semibold text-primary">Por que a capacidade está no máximo?</p>
                    <p className="mb-2 text-[11px] leading-relaxed text-secondary">
                      {capacity ? (
                        <>Todos os <span className="font-semibold text-amber">{capacity.max_concurrent_ingest}</span> slots de ingestão simultânea estão ocupados
                        ({capacity.running_ingest_jobs}/{capacity.max_concurrent_ingest} em uso).
                        {capacity.er_running && " A Resolução de Entidades também está ativa."}</>
                      ) : (
                        <>Todos os slots de ingestão simultânea estão ocupados.</>
                      )}
                    </p>
                    {(() => {
                      const activeJobs = sources
                        .filter((s) => s.runtime.active_job_names && s.runtime.active_job_names.length > 0)
                        .flatMap((s) => s.runtime.active_job_names!.map((job) => ({ connector: s.connector_label || s.connector, job })));
                      return activeJobs.length > 0 ? (
                        <div className="mb-1.5">
                          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted">Jobs ativos agora:</p>
                          <ul className="space-y-0.5">
                            {activeJobs.slice(0, 6).map((aj, i) => (
                              <li key={i} className="flex items-center gap-1.5 text-[11px] text-secondary">
                                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent animate-pulse" />
                                <span className="truncate font-medium">{aj.connector}</span>
                                <span className="text-muted">— {aj.job}</span>
                              </li>
                            ))}
                            {activeJobs.length > 6 && (
                              <li className="text-[10px] text-muted">+{activeJobs.length - 6} mais...</li>
                            )}
                          </ul>
                        </div>
                      ) : null;
                    })()}
                    <p className="text-[10px] text-muted">Novos jobs serão enfileirados até que um slot seja liberado.</p>
                  </div>
                </span>
              )}
              <button
                onClick={() => setPipelineModalOpen(true)}
                className="inline-flex items-center gap-2 rounded-lg border border-accent/40 bg-accent-subtle px-3 py-2 text-xs font-semibold text-accent transition-opacity hover:opacity-80"
              >
                <Play className="h-3.5 w-3.5" />
                Executar Pipeline
              </button>
              <div className="rounded-lg border border-border bg-surface-base px-3 py-2 text-right">
                <p className="flex items-center gap-1 font-mono text-[10px] font-semibold uppercase tracking-wide text-muted">
                  <Clock className="h-3 w-3" />
                  Snapshot
                </p>
                <p className="mt-0.5 font-mono tabular-nums text-xs font-medium text-primary">
                  {summary?.snapshot_at
                    ? new Date(summary.snapshot_at).toLocaleString("pt-BR")
                    : "Aguardando dados"}
                </p>
              </div>
            </div>
          </div>

          {/* KPI Strip */}
          <div className="mt-6">
            <KpiStrip summary={summary} loading={summaryLoading} />
          </div>
        </div>
      </div>

      {/* ── Body ────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6 space-y-8">

        {summaryError && (
          <div className="rounded-lg border border-error/20 bg-error-subtle px-3 py-2 text-sm text-error">
            {summaryError}
          </div>
        )}

        {/* Pipeline */}
        {!summaryLoading && summary && <PipelineStrip summary={summary} />}

        {/* ── Sources section ──────────────────────────────────── */}
        <section>
          <div className="flex flex-wrap items-end justify-between gap-3 mb-5">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-widest text-muted">Fontes de Dados</p>
              <p className="text-sm font-semibold text-primary mt-0.5">
                {filteredSources.length} de {sources.length} fontes
              </p>
              <p className="text-xs text-secondary mt-0.5">Clique em "Ver diagnóstico detalhado" para abrir o painel completo de cada fonte</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <label className="flex items-center gap-2 rounded-lg border border-border bg-surface-card px-3 py-1.5">
                <Search className="h-3.5 w-3.5 text-muted shrink-0" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Buscar fonte..."
                  className="w-36 bg-transparent text-xs text-primary outline-none placeholder:text-placeholder"
                />
              </label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as "" | CoverageStatus)}
                className="rounded-lg border border-border bg-surface-card px-3 py-1.5 text-xs text-primary outline-none"
              >
                <option value="">Todos os status</option>
                <option value="ok">OK</option>
                <option value="warning">Atenção</option>
                <option value="stale">Defasado</option>
                <option value="error">Erro</option>
                <option value="pending">Pendente</option>
              </select>
              <label className="flex items-center gap-2 rounded-lg border border-border bg-surface-card px-3 py-1.5 cursor-pointer text-xs text-secondary">
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
            <div className="rounded-lg border border-error/20 bg-error-subtle px-3 py-2 text-sm text-error mb-4">
              {sourcesError}
            </div>
          )}

          {sourcesLoading ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="h-56 rounded-xl border border-border bg-surface-card animate-pulse" />
              ))}
            </div>
          ) : filteredSources.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-border bg-surface-card py-12 gap-2">
              <AlertTriangle className="h-7 w-7 text-muted" />
              <p className="text-sm text-muted">Nenhuma fonte encontrada com os filtros aplicados.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {filteredSources.map((item) => (
                <SourceCard key={item.connector} item={item} />
              ))}
            </div>
          )}
        </section>

        {/* ── Analytics section ────────────────────────────────── */}
        <section>
          <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-widest text-muted">Cobertura Analítica por Tipologia</p>
              <p className="text-sm font-semibold text-primary mt-0.5">
                {analytics ? `${analytics.items.length} tipologias` : "Carregando…"}
              </p>
              <p className="text-xs text-secondary mt-0.5">Aptidão para detecção baseada em domínios disponíveis e execuções recentes</p>
            </div>
            {analytics && (
              <div className="flex gap-2 flex-wrap">
                {[
                  { label: `${analytics.summary.apt_count} aptas`,             cls: "text-success border-success/30 bg-success/5"    },
                  { label: `${analytics.summary.blocked_count} bloqueadas`,    cls: "text-error   border-error/30   bg-error/5"      },
                  { label: `${analytics.summary.with_signals_30d} c/ sinais`,  cls: "text-accent  border-accent/30  bg-accent-subtle" },
                ].map((s) => (
                  <span key={s.label} className={`rounded-full border px-2.5 py-0.5 font-mono text-[10px] font-bold ${s.cls}`}>
                    {s.label}
                  </span>
                ))}
              </div>
            )}
          </div>

          {analyticsLoading ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 9 }).map((_, i) => (
                <div key={i} className="h-40 rounded-xl border border-border bg-surface-card animate-pulse" />
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
    </div>
    </>
  );
}
