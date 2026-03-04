"use client";

import { useEffect, useMemo, useState } from "react";
import {
  getCoverageV2Analytics,
  getCoverageV2SourcePreview,
  getCoverageV2Sources,
  getCoverageV2Summary,
} from "@/lib/api";
import { CoverageSourcePreviewDrawer } from "@/components/coverage/CoverageSourcePreviewDrawer";
import type {
  AnalyticalCoverageItem,
  CoverageStatus,
  CoverageV2AnalyticsResponse,
  CoverageV2SourceItem,
  CoverageV2SourcePreviewResponse,
  CoverageV2SummaryResponse,
} from "@/lib/types";
import { formatNumber } from "@/lib/utils";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Clock,
  Database,
  FileText,
  Search,
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
    { label: "Fontes",      value: t?.connectors ?? 0,                    sub: null,                            dot: null              },
    { label: "Jobs",        value: t?.jobs ?? 0,                           sub: `${t?.jobs_enabled ?? 0} ativos`, dot: null              },
    { label: "Sinais",      value: formatNumber(t?.signals_total ?? 0),    sub: null,                            dot: null              },
    { label: "OK",          value: sc?.ok ?? 0,                            sub: null,                            dot: "bg-success"      },
    { label: "Atenção",     value: sc?.warning ?? 0,                       sub: null,                            dot: "bg-amber"        },
    { label: "Defasado",    value: sc?.stale ?? 0,                         sub: null,                            dot: "bg-yellow-500"   },
    { label: "Erro",        value: sc?.error ?? 0,                         sub: null,                            dot: "bg-error"        },
    { label: "Travados",    value: rt?.failed_or_stuck ?? 0,               sub: null,                            dot: rt?.failed_or_stuck ? "bg-error" : "bg-muted/40" },
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
  done:       { label: "Concluído",    icon: <CheckCircle2 className="h-4 w-4" />, ring: "border-success",     bg: "bg-success/10",      text: "text-success"     },
  processing: { label: "Processando",  icon: <Activity className="h-4 w-4" />,     ring: "border-accent",      bg: "bg-accent/10",       text: "text-accent"      },
  warning:    { label: "Atenção",      icon: <AlertTriangle className="h-4 w-4" />, ring: "border-amber",       bg: "bg-amber/10",        text: "text-amber"       },
  error:      { label: "Erro",         icon: <XCircle className="h-4 w-4" />,       ring: "border-error",       bg: "bg-error/10",        text: "text-error"       },
  pending:    { label: "Pendente",     icon: <Clock className="h-4 w-4" />,         ring: "border-border",      bg: "bg-surface-subtle",  text: "text-muted"       },
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
    <div className="rounded-xl border border-border bg-surface-card p-5">
      <div className="flex items-center justify-between mb-5">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted">Pipeline de Ingestão</p>
          <p className="text-xs text-secondary mt-0.5">Estado atual de cada etapa de processamento</p>
        </div>
        <span className={`rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${ocfg.cls}`}>
          {ocfg.label}
        </span>
      </div>

      <div className="flex items-start gap-0 overflow-x-auto pb-1">
        {stages.map((stage, i) => {
          const scfg = STAGE_STATUS[stage.status] ?? STAGE_STATUS.pending;
          return (
            <div key={stage.code} className="flex items-center shrink-0">
              <div className="flex flex-col items-center gap-1.5 min-w-[100px] px-2">
                <div className={`flex h-9 w-9 items-center justify-center rounded-full border-2 ${scfg.ring} ${scfg.bg} ${scfg.text}`}>
                  {scfg.icon}
                </div>
                <p className="font-mono text-[10px] text-center text-primary font-semibold leading-tight">{stage.label}</p>
                <p className={`font-mono text-[9px] font-bold uppercase ${scfg.text}`}>{scfg.label}</p>
                {stage.reason && stage.status !== "done" && (
                  <p className="text-[9px] text-secondary text-center leading-tight max-w-[90px]">{stage.reason}</p>
                )}
              </div>
              {i < stages.length - 1 && (
                <ChevronRight className="h-4 w-4 text-border shrink-0 mx-1" />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Source card (fully expanded) ─────────────────────────────────────────────

function SourceCard({ item, onDiagnose }: { item: CoverageV2SourceItem; onDiagnose: (item: CoverageV2SourceItem) => void }) {
  const cfg = STATUS_CFG[item.worst_status] ?? STATUS_CFG.pending;
  const totalJobs = Object.values(item.status_counts).reduce((a, b) => a + b, 0);

  const statusBar = [
    { key: "ok"      as CoverageStatus, count: item.status_counts.ok,      color: "bg-success"    },
    { key: "warning" as CoverageStatus, count: item.status_counts.warning,  color: "bg-amber"      },
    { key: "stale"   as CoverageStatus, count: item.status_counts.stale,    color: "bg-yellow-500" },
    { key: "error"   as CoverageStatus, count: item.status_counts.error,    color: "bg-error"      },
    { key: "pending" as CoverageStatus, count: item.status_counts.pending,  color: "bg-muted/30"   },
  ].filter((s) => s.count > 0);

  return (
    <div className={`rounded-xl border ${cfg.border} bg-surface-card flex flex-col gap-4 p-4`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-display text-sm font-bold text-primary capitalize leading-snug">
            {item.connector_label}
          </h3>
          <p className="font-mono text-[10px] text-muted mt-0.5">{item.connector}</p>
        </div>
        <StatusBadge status={item.worst_status} />
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
                className={`${s.color}`}
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

      {/* Diagnose CTA */}
      <button
        onClick={() => onDiagnose(item)}
        className="mt-auto flex w-full items-center justify-center gap-1.5 rounded-lg border border-border bg-surface-base px-3 py-2 text-xs font-semibold text-secondary transition hover:border-accent/40 hover:bg-accent-subtle/20 hover:text-accent"
      >
        <Search className="h-3.5 w-3.5" />
        Diagnosticar fonte
      </button>
    </div>
  );
}

// ── Typology card ─────────────────────────────────────────────────────────────

function TypologyCard({ item }: { item: AnalyticalCoverageItem }) {
  const domainTotal = item.required_domains.length;
  const domainAvail = item.domains_available.length;
  const pct = domainTotal > 0 ? Math.round((domainAvail / domainTotal) * 100) : 0;
  const barColor = item.apt ? "bg-success" : pct > 0 ? "bg-amber" : "bg-error";
  const borderColor = item.apt ? "border-success/20" : pct > 0 ? "border-amber/20" : "border-error/20";

  return (
    <div className={`rounded-xl border ${borderColor} bg-surface-card p-4 space-y-3`}>
      {/* Header */}
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

      {/* Domain coverage bar */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <p className="font-mono text-[10px] text-muted">Domínios cobertos</p>
          <p className="font-mono text-[10px] text-muted">{domainAvail}/{domainTotal}</p>
        </div>
        <div className="h-1.5 rounded-full bg-surface-subtle overflow-hidden">
          <div className={`h-full ${barColor} transition-all`} style={{ width: `${pct}%` }} />
        </div>
      </div>

      {/* Domain tags */}
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

      {/* Execution stats */}
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

      {/* Evidence level + corruption types */}
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

  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<CoverageV2SourcePreviewResponse | null>(null);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"" | CoverageStatus>("");
  const [enabledOnly, setEnabledOnly] = useState(false);

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
    setSourcesLoading(true);
    getCoverageV2Sources({ limit: 100, enabled_only: enabledOnly })
      .then((r) => { if (active) setSources(r.items); })
      .catch(() => { if (active) setSourcesError("Falha ao carregar fontes de dados."); })
      .finally(() => { if (active) setSourcesLoading(false); });
    return () => { active = false; };
  }, [enabledOnly]);

  useEffect(() => {
    let active = true;
    getCoverageV2Analytics()
      .then((d) => { if (active) setAnalytics(d); })
      .catch(() => {})
      .finally(() => { if (active) setAnalyticsLoading(false); });
    return () => { active = false; };
  }, []);

  function handleDiagnose(item: CoverageV2SourceItem) {
    setPreviewOpen(true);
    setPreviewLoading(true);
    setPreviewError(null);
    setPreviewData(null);
    getCoverageV2SourcePreview(item.connector, { runs_limit: 12 })
      .then(setPreviewData)
      .catch(() => setPreviewError("Não foi possível carregar o diagnóstico detalhado desta fonte."))
      .finally(() => setPreviewLoading(false));
  }

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
        const order: CoverageStatus[] = ["error", "warning", "stale", "ok", "pending"];
        return order.indexOf(a.worst_status) - order.indexOf(b.worst_status);
      });
  }, [sources, search, statusFilter]);

  return (
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
            <div className="shrink-0 rounded-lg border border-border bg-surface-base px-3 py-2 text-right">
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
              <p className="text-xs text-secondary mt-0.5">Cada card mostra o estado completo de uma fonte pública</p>
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
                <SourceCard key={item.connector} item={item} onDiagnose={handleDiagnose} />
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
                  { label: `${analytics.summary.apt_count} aptas`,             cls: "text-success border-success/30 bg-success/5"   },
                  { label: `${analytics.summary.blocked_count} bloqueadas`,    cls: "text-error   border-error/30   bg-error/5"     },
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

      {/* ── Preview drawer ───────────────────────────────────────── */}
      <CoverageSourcePreviewDrawer
        open={previewOpen}
        loading={previewLoading}
        error={previewError}
        data={previewData}
        onClose={() => setPreviewOpen(false)}
      />
    </div>
  );
}
