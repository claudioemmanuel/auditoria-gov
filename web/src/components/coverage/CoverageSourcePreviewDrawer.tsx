"use client";

import Link from "next/link";
import type { CoverageStatus, CoverageV2LatestRun, CoverageV2SourcePreviewResponse } from "@/lib/types";
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  FileText,
  Lightbulb,
  Package,
  TriangleAlert,
  X,
  Zap,
} from "lucide-react";

interface CoverageSourcePreviewDrawerProps {
  open: boolean;
  loading: boolean;
  error: string | null;
  data: CoverageV2SourcePreviewResponse | null;
  onClose: () => void;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const STATUS_CFG: Record<CoverageStatus, { label: string; dot: string; text: string; border: string; bg: string }> = {
  ok:      { label: "OK",       dot: "bg-success",    text: "text-success",    border: "border-success/30",    bg: "bg-success/5"    },
  warning: { label: "Atenção",  dot: "bg-amber",       text: "text-amber",       border: "border-amber/30",       bg: "bg-amber/5"       },
  stale:   { label: "Defasado", dot: "bg-yellow-500",  text: "text-yellow-600",  border: "border-yellow-500/30",  bg: "bg-yellow-500/5"  },
  error:   { label: "Erro",     dot: "bg-error",       text: "text-error",       border: "border-error/30",       bg: "bg-error/5"       },
  pending: { label: "Pendente", dot: "bg-muted/60",    text: "text-muted",       border: "border-border",         bg: "bg-surface-base"  },
};

const RUN_STATUS_CFG: Record<string, { dot: string; text: string; label: string }> = {
  completed: { dot: "bg-success",    text: "text-success",    label: "Concluído"    },
  running:   { dot: "bg-accent",     text: "text-accent",     label: "Executando"   },
  failed:    { dot: "bg-error",      text: "text-error",      label: "Falhou"       },
  stuck:     { dot: "bg-amber",      text: "text-amber",      label: "Travado"      },
  pending:   { dot: "bg-muted/60",   text: "text-muted",      label: "Pendente"     },
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

function RunStatusDot({ status, isStuck }: { status: string; isStuck: boolean }) {
  const key = isStuck ? "stuck" : status;
  const cfg = RUN_STATUS_CFG[key] ?? RUN_STATUS_CFG.pending;
  return <span className={`inline-block h-2 w-2 rounded-full ${cfg.dot}`} />;
}

function formatLag(hours: number | null | undefined): string {
  if (hours == null) return "—";
  if (hours < 1) return "<1h";
  if (hours < 24) return `${Math.round(hours)}h`;
  return `${Math.round(hours / 24)}d`;
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

// ── Run card (inline in jobs section) ────────────────────────────────────────

function RunCard({ run, linkToDetail }: { run: CoverageV2LatestRun; linkToDetail?: boolean }) {
  const key = run.is_stuck ? "stuck" : run.status;
  const cfg = RUN_STATUS_CFG[key] ?? RUN_STATUS_CFG.pending;

  return (
    <div className="rounded-lg border border-border bg-surface-base p-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <RunStatusDot status={run.status} isStuck={run.is_stuck} />
          <span className={`font-mono text-xs font-bold ${cfg.text}`}>
            {run.is_stuck ? "Travado" : RUN_STATUS_CFG[run.status]?.label ?? run.status}
          </span>
          <span className="font-mono text-[10px] text-muted">
            {formatDuration(run.started_at, run.finished_at)}
          </span>
        </div>
        {linkToDetail && (
          <Link
            href={`/coverage/run/${run.id}`}
            className="flex items-center gap-1 font-mono text-[10px] text-accent hover:underline"
          >
            Detalhar
            <ArrowUpRight className="h-2.5 w-2.5" />
          </Link>
        )}
      </div>

      {/* Times */}
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

      {/* Items */}
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

      {/* Error message */}
      {run.error_message && (
        <div className="flex items-start gap-1.5 rounded border border-error/20 bg-error/5 px-2 py-1.5">
          <AlertTriangle className="h-3 w-3 shrink-0 text-error mt-0.5" />
          <p className="font-mono text-[10px] text-error leading-snug">{run.error_message}</p>
        </div>
      )}
    </div>
  );
}

// ── Main drawer ───────────────────────────────────────────────────────────────

export function CoverageSourcePreviewDrawer({
  open,
  loading,
  error,
  data,
  onClose,
}: CoverageSourcePreviewDrawerProps) {
  if (!open) return null;

  const connector = data?.connector;
  const statusCounts = connector?.status_counts;
  const totalJobs = statusCounts
    ? Object.values(statusCounts).reduce((a, b) => a + b, 0)
    : 0;

  const statusBar = statusCounts
    ? [
        { key: "ok"      as CoverageStatus, count: statusCounts.ok,      color: "bg-success"    },
        { key: "warning" as CoverageStatus, count: statusCounts.warning,  color: "bg-amber"      },
        { key: "stale"   as CoverageStatus, count: statusCounts.stale,    color: "bg-yellow-500" },
        { key: "error"   as CoverageStatus, count: statusCounts.error,    color: "bg-error"      },
        { key: "pending" as CoverageStatus, count: statusCounts.pending,  color: "bg-muted/30"   },
      ].filter((s) => s.count > 0)
    : [];

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 z-50 flex h-full w-full max-w-xl flex-col bg-surface-card shadow-2xl">

        {/* ── Header ──────────────────────────────────────────── */}
        <div className="flex items-start justify-between gap-3 border-b border-border px-5 py-4">
          <div>
            <h2 className="font-display text-base font-bold text-primary">Diagnóstico da Fonte</h2>
            <p className="text-xs text-muted mt-0.5">Drill-down operacional completo — jobs, execuções e insights</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted transition hover:bg-surface-subtle hover:text-primary"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* ── Scrollable body ──────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">

          {/* Loading */}
          {loading && (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className={`h-${i === 0 ? "20" : "16"} rounded-xl border border-border bg-surface-base animate-pulse`} />
              ))}
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="flex items-start gap-2 rounded-xl border border-error/20 bg-error/5 p-4">
              <AlertTriangle className="h-4 w-4 text-error shrink-0 mt-0.5" />
              <p className="text-sm text-error">{error}</p>
            </div>
          )}

          {!loading && !error && data && (
            <>
              {/* ── Source summary card ─────────────────────── */}
              <div className={`rounded-xl border ${STATUS_CFG[connector?.worst_status ?? "pending"].border} bg-surface-base p-4 space-y-3`}>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-display text-sm font-bold text-primary capitalize leading-snug">
                      {connector?.connector_label}
                    </h3>
                    <p className="font-mono text-[10px] text-muted mt-0.5">{connector?.connector}</p>
                  </div>
                  {connector && <StatusBadge status={connector.worst_status} />}
                </div>

                {/* Job counts */}
                <div className="flex items-center gap-4 text-xs text-muted">
                  <span className="flex items-center gap-1">
                    <FileText className="h-3 w-3" />
                    <span className="font-mono font-bold text-primary">{connector?.job_count}</span> jobs
                  </span>
                  <span className="flex items-center gap-1 text-accent">
                    <Zap className="h-3 w-3" />
                    <span className="font-mono font-bold">{connector?.enabled_job_count}</span> habilitados
                  </span>
                </div>

                {/* Status distribution bar */}
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
                      {statusBar.map((s) => (
                        <span key={s.key} className="flex items-center gap-1 text-[10px] text-muted">
                          <span className={`h-1.5 w-1.5 rounded-full ${s.color}`} />
                          {STATUS_CFG[s.key]?.label}: <span className="font-mono font-bold text-primary">{s.count}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* ── Insights ────────────────────────────────── */}
              {data.insights.length > 0 && (
                <section>
                  <p className="font-mono text-[10px] uppercase tracking-widest text-muted mb-2">Insights</p>
                  <div className="space-y-2">
                    {data.insights.map((insight, i) => (
                      <div key={i} className="flex items-start gap-2 rounded-lg border border-accent/20 bg-accent-subtle/30 px-3 py-2.5">
                        <Lightbulb className="h-3.5 w-3.5 shrink-0 text-accent mt-0.5" />
                        <p className="text-xs text-secondary leading-relaxed">{insight}</p>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* ── Jobs ────────────────────────────────────── */}
              <section>
                <p className="font-mono text-[10px] uppercase tracking-widest text-muted mb-2">
                  Jobs ({data.jobs.length})
                </p>
                <div className="space-y-3">
                  {data.jobs.map((job) => {
                    const scfg = STATUS_CFG[job.status] ?? STATUS_CFG.pending;
                    return (
                      <div key={job.job} className={`rounded-xl border ${scfg.border} bg-surface-base p-4 space-y-3`}>
                        {/* Job header */}
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <div className="flex items-center gap-2 flex-wrap mb-0.5">
                              <span className="font-mono text-xs font-bold text-primary truncate">{job.job}</span>
                              {!job.enabled_in_mvp && (
                                <span className="rounded-full border border-border bg-surface-subtle px-1.5 py-0.5 text-[9px] font-bold uppercase text-muted">
                                  Desab.
                                </span>
                              )}
                            </div>
                            <p className="font-mono text-[10px] text-accent">{job.domain}</p>
                            {job.description && (
                              <p className="text-[11px] text-secondary mt-1 leading-snug">{job.description}</p>
                            )}
                          </div>
                          <StatusBadge status={job.status} />
                        </div>

                        {/* Job stats */}
                        <div className="grid grid-cols-2 gap-2 text-[10px]">
                          <div>
                            <p className="font-mono text-[9px] uppercase tracking-wide text-muted mb-0.5">Itens totais</p>
                            <p className="font-mono font-bold text-primary">{job.total_items.toLocaleString("pt-BR")}</p>
                          </div>
                          <div>
                            <p className="font-mono text-[9px] uppercase tracking-wide text-muted mb-0.5">Defasagem</p>
                            <p className={`font-mono font-bold ${
                              job.freshness_lag_hours == null ? "text-muted" :
                              job.freshness_lag_hours > 48 ? "text-error" :
                              job.freshness_lag_hours > 24 ? "text-amber" : "text-success"
                            }`}>
                              {formatLag(job.freshness_lag_hours)}
                            </p>
                          </div>
                          <div className="col-span-2">
                            <p className="font-mono text-[9px] uppercase tracking-wide text-muted mb-0.5">Último sucesso</p>
                            <p className="font-mono text-primary">
                              {job.last_success_at ? fmtDate(job.last_success_at) : "Não registrado"}
                            </p>
                          </div>
                        </div>

                        {/* Latest run */}
                        {job.latest_run && (
                          <div>
                            <p className="font-mono text-[9px] uppercase tracking-wide text-muted mb-1.5">Execução mais recente</p>
                            <RunCard run={job.latest_run} linkToDetail />
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </section>

              {/* ── Recent runs timeline ─────────────────────── */}
              {data.recent_runs.length > 0 && (
                <section>
                  <p className="font-mono text-[10px] uppercase tracking-widest text-muted mb-2">
                    Execuções recentes ({data.recent_runs.length})
                  </p>
                  <div className="space-y-2">
                    {data.recent_runs.map((run) => (
                      <RunCard key={run.id} run={run} linkToDetail />
                    ))}
                  </div>
                </section>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}
