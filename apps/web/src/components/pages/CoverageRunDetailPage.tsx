"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getIngestRunDetail } from "@/lib/api";
import { Button } from "@/components/Button";
import { PageHeader } from "@/components/PageHeader";
import { formatDateTime, formatNumber } from "@/lib/utils";
import type { IngestRunDetailResponse, IngestRunFieldProfile } from "@/lib/types";
import {
  Activity,
  AlertTriangle,
  ArrowDownUp,
  ArrowLeft,
  BarChart3,
  Braces,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CircleX,
  Clock,
  Copy,
  Database,
  FileJson,
  FileText,
  Hash,
  Loader2,
  MapPin,
  RefreshCw,
  Timer,
  Zap,
} from "lucide-react";

// ── Status config ─────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { label: string; border: string; bg: string; text: string; dot: string; Icon: typeof CheckCircle2 }> = {
  completed: { label: "Concluído",    border: "border-success/30", bg: "bg-success/5",  text: "text-success", dot: "bg-success",  Icon: CheckCircle2 },
  running:   { label: "Em execução",  border: "border-accent/30",  bg: "bg-accent/5",   text: "text-accent",  dot: "bg-accent",   Icon: Loader2      },
  yielded:   { label: "Cedeu vez",    border: "border-amber/30",   bg: "bg-amber/5",    text: "text-amber",   dot: "bg-amber",    Icon: Clock        },
  failed:    { label: "Falhou",       border: "border-error/30",   bg: "bg-error/5",    text: "text-error",   dot: "bg-error",    Icon: CircleX      },
  error:     { label: "Erro",         border: "border-error/30",   bg: "bg-error/5",    text: "text-error",   dot: "bg-error",    Icon: CircleX      },
};

function getStatusCfg(status: string) {
  return STATUS_CONFIG[status] ?? {
    label: status, border: "border-border", bg: "bg-surface-base", text: "text-muted", dot: "bg-muted/50", Icon: Clock,
  };
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtDate(value?: string | null): string {
  if (!value) return "—";
  return formatDateTime(value);
}

function pct(value: number, total: number): number {
  if (total <= 0) return 0;
  return Math.round((value / total) * 10000) / 100;
}

function formatDuration(startedAt?: string | null, finishedAt?: string | null): string {
  if (!startedAt) return "—";
  const ms = (finishedAt ? new Date(finishedAt) : new Date()).getTime() - new Date(startedAt).getTime();
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  const m = Math.floor(ms / 60_000);
  const s = Math.round((ms % 60_000) / 1000);
  return `${m}min ${s}s`;
}

function stringifyJson(value: unknown): string {
  try { return JSON.stringify(value, null, 2); } catch { return String(value); }
}

function formatStructuredValue(value: unknown): string {
  if (typeof value === "string") {
    const t = value.trim();
    if (t.startsWith("{") || t.startsWith("[")) {
      try { return JSON.stringify(JSON.parse(t), null, 2); } catch { return value; }
    }
    return value;
  }
  return stringifyJson(value);
}

function shouldRenderAsBlock(v: unknown): boolean {
  if (typeof v !== "string") return true;
  const t = v.trim();
  return t.startsWith("{") || t.startsWith("[") || t.includes("\n");
}

function coverageColor(p: number): string {
  if (p >= 90) return "bg-success";
  if (p >= 50) return "bg-amber";
  return "bg-error";
}

// ── KPI Card ──────────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, icon: Icon }: {
  label: string; value: string | number; sub?: string; icon: typeof Database;
}) {
  return (
    <div className="rounded-xl border border-border bg-surface-card px-4 py-4">
      <div className="flex items-center gap-1.5 mb-2">
        <Icon className="h-3.5 w-3.5 text-accent shrink-0" />
        <p className="font-mono text-[9px] uppercase tracking-widest text-muted">{label}</p>
      </div>
      <p className="font-mono text-2xl font-bold tabular-nums text-primary leading-none">
        {typeof value === "number" ? formatNumber(value) : value}
      </p>
      {sub && <p className="font-mono text-[10px] text-muted mt-1.5">{sub}</p>}
    </div>
  );
}

// ── Field profile row ─────────────────────────────────────────────────────────

function FieldProfileRow({ field, total }: { field: IngestRunFieldProfile; total: number }) {
  return (
    <tr className="border-b border-border last:border-0 hover:bg-surface-subtle/50 transition-colors">
      <td className="px-4 py-3 align-top">
        <code className="rounded-md border border-border bg-surface-base px-1.5 py-0.5 font-mono text-xs text-accent">
          {field.key}
        </code>
      </td>
      <td className="px-4 py-3 align-middle">
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-20 rounded-full bg-surface-subtle overflow-hidden">
            <div
              className={`h-full ${coverageColor(field.coverage_pct)} transition-all`}
              style={{ width: `${Math.min(field.coverage_pct, 100)}%` }}
            />
          </div>
          <span className="font-mono text-xs font-bold text-primary tabular-nums">{field.coverage_pct}%</span>
          <span className="font-mono text-[10px] text-muted">({field.present_count}/{total})</span>
        </div>
      </td>
      <td className="px-4 py-3 align-top">
        <div className="flex flex-wrap gap-1">
          {field.detected_types.map((t) => (
            <span key={t} className="rounded-full border border-accent/20 bg-accent-subtle px-1.5 py-0.5 font-mono text-[10px] font-bold text-accent">
              {t}
            </span>
          ))}
        </div>
      </td>
      <td className="px-4 py-3 align-top max-w-xs">
        <div className="space-y-1.5">
          {field.examples.length === 0 ? (
            <span className="font-mono text-[10px] text-muted">—</span>
          ) : (
            field.examples.map((ex, i) => {
              const display = formatStructuredValue(ex);
              return shouldRenderAsBlock(display) ? (
                <pre key={i} className="max-h-28 overflow-auto rounded-lg border border-border bg-surface-base px-2 py-1.5 font-mono text-[10px] leading-relaxed whitespace-pre-wrap break-words text-secondary">
                  {display}
                </pre>
              ) : (
                <p key={i} className="rounded-lg border border-border bg-surface-base px-2 py-1.5 font-mono text-[10px] text-secondary break-words">
                  {display}
                </p>
              );
            })
          )}
        </div>
      </td>
    </tr>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

const SAMPLES_PER_PAGE = 10;


export default function CoverageRunDetailPage() {
  const params = useParams<{ id: string }>();
  const runId = params.id;

  const [detail, setDetail]               = useState<IngestRunDetailResponse | null>(null);
  const [loading, setLoading]             = useState(true);
  const [error, setError]                 = useState<string | null>(null);
  const [fieldProfileOpen, setFieldProfileOpen] = useState(false);
  const [samplesOpen, setSamplesOpen]     = useState(false);
  const [openSamples, setOpenSamples]     = useState<Set<number>>(() => new Set());
  const [samplesPage, setSamplesPage]     = useState(0);

  function fetchDetail() {
    if (!runId) return;
    setLoading(true);
    setError(null);
    getIngestRunDetail(runId)
      .then(setDetail)
      .catch(() => setError("Não foi possível carregar o detalhe da execução."))
      .finally(() => setLoading(false));
  }

  function fetchSilent() {
    if (!runId) return;
    getIngestRunDetail(runId).then(setDetail).catch(() => {});
  }

  // Initial fetch
  useEffect(fetchDetail, [runId]);

  // Poll every 5s while the run is still active
  useEffect(() => {
    if (detail?.run.status !== "running") return;
    const interval = setInterval(fetchSilent, 5_000);
    return () => clearInterval(interval);
  }, [detail?.run.status, runId]);

  // Live elapsed timer for running jobs
  const [nowMs, setNowMs] = useState(() => Date.now());
  useEffect(() => {
    if (detail?.run.status !== "running") return;
    const id = setInterval(() => setNowMs(Date.now()), 1_000);
    return () => clearInterval(id);
  }, [detail?.run.status]);

  const normalizedPct = useMemo(() => {
    if (!detail) return 0;
    return pct(detail.run.items_normalized, detail.run.items_fetched);
  }, [detail]);

  const dupPct = useMemo(() => {
    if (!detail || detail.summary.records_stored === 0) return 0;
    return pct(detail.summary.duplicate_raw_ids, detail.summary.records_stored);
  }, [detail]);

  const isRunning = detail?.run.status === "running";
  const isYielded = detail?.run.status === "yielded";
  const startMs = detail?.run.started_at ? new Date(detail.run.started_at).getTime() : 0;
  const liveElapsedMs = startMs > 0 ? nowMs - startMs : 0;
  const liveElapsedStr = isRunning && liveElapsedMs > 0
    ? liveElapsedMs >= 3600_000
      ? `${Math.floor(liveElapsedMs / 3600_000)}h ${Math.floor((liveElapsedMs % 3600_000) / 60_000)}min`
      : liveElapsedMs >= 60_000
        ? `${Math.floor(liveElapsedMs / 60_000)}min ${Math.floor((liveElapsedMs % 60_000) / 1_000)}s`
        : `${Math.floor(liveElapsedMs / 1_000)}s`
    : null;

  const duration = detail ? formatDuration(detail.run.started_at, detail.run.finished_at) : "—";
  const statusCfg = detail ? getStatusCfg(detail.run.status) : getStatusCfg("running");
  const StatusIcon = statusCfg.Icon;

  // Determine current phase
  const currentPhase: "ingest" | "normalize" | "done" | "error" = !detail ? "ingest"
    : detail.run.status === "error" ? "error"
    : isRunning ? "ingest"
    : normalizedPct >= 100 ? "done"
    : "normalize";

  const totalSamplePages = detail ? Math.ceil(detail.samples.length / SAMPLES_PER_PAGE) : 0;
  const globalOffset = samplesPage * SAMPLES_PER_PAGE;
  const pagedSamples = detail?.samples.slice(globalOffset, globalOffset + SAMPLES_PER_PAGE) ?? [];

  // ── Loading ────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen">
        <div className="border-b border-border bg-surface-card">
          <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6">
            <div className="flex items-start gap-4">
              <div className="h-12 w-12 rounded-xl border border-border bg-surface-subtle animate-pulse shrink-0" />
              <div className="space-y-2 flex-1">
                <div className="h-4 w-24 rounded bg-surface-subtle animate-pulse" />
                <div className="h-7 w-64 rounded bg-surface-subtle animate-pulse" />
                <div className="h-3 w-40 rounded bg-surface-subtle animate-pulse" />
              </div>
            </div>
          </div>
        </div>
        <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6 space-y-4">
          <div className="grid grid-cols-4 gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-20 rounded-xl border border-border bg-surface-card animate-pulse" />
            ))}
          </div>
          <div className="h-40 rounded-xl border border-border bg-surface-card animate-pulse" />
          <div className="h-64 rounded-xl border border-border bg-surface-card animate-pulse" />
        </div>
      </div>
    );
  }

  // ── Error ──────────────────────────────────────────────────────────────────
  if (error || !detail) {
    return (
      <div className="min-h-screen">
        <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6">
          <PageHeader
            eyebrow="PIPELINE"
            title="Detalhe da Execução"
            description="Não foi possível carregar os dados desta execução."
            variant="hero"
            icon={<AlertTriangle className="h-5 w-5" />}
          />
        </div>
        <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6">
          <div className="flex flex-col items-center justify-center rounded-xl border border-error/20 bg-error/5 py-16 gap-4">
            <AlertTriangle className="h-10 w-10 text-error" />
            <div className="text-center">
              <p className="font-semibold text-primary">{error ?? "Detalhe indisponível"}</p>
              <p className="text-xs text-muted mt-1">Verifique a conexão com a API e tente novamente.</p>
            </div>
            <Button onClick={fetchDetail}>
              <RefreshCw className="h-3.5 w-3.5" />
              Tentar novamente
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">

      <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6">
        <PageHeader
          breadcrumbs={[
            { label: "Cobertura", href: "/coverage" },
            { label: "Execução" },
          ]}
          eyebrow="PIPELINE"
          title={`${detail.run.connector} / ${detail.run.job}`}
          description="Detalhe operacional da execução, diagnóstico de normalização e amostras processadas."
          variant="hero"
          icon={<Database className="h-5 w-5" />}
          actions={
            <div className="flex shrink-0 items-center gap-3">
              <div className="flex items-center gap-1.5 text-xs text-muted">
                <Timer className="h-3.5 w-3.5" />
                <span className="font-mono tabular-nums">{duration}</span>
              </div>
              <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-wide ${statusCfg.border} ${statusCfg.bg} ${statusCfg.text}`}>
                <StatusIcon className={`h-3.5 w-3.5 ${detail.run.status === "running" ? "animate-spin" : ""}`} />
                {statusCfg.label}
              </span>
            </div>
          }
          stats={[
            { label: "Domínio", value: detail.job.domain ?? "—" },
            { label: "Início", value: fmtDate(detail.run.started_at), mono: true },
            { label: "Fim", value: fmtDate(detail.run.finished_at), mono: true },
          ]}
        />

        <div className="mt-4">
          <Link
            href="/coverage"
            className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-accent transition-colors"
          >
            <ArrowLeft className="h-3 w-3" />
            Voltar para Cobertura
          </Link>
        </div>
      </div>

      {/* ── Body ────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6 space-y-6">

        {/* ── Live progress (prominent for running/yielded) ───── */}
        {(isRunning || isYielded) && (
          <section className={`rounded-xl border-2 p-5 space-y-4 ${
            isRunning ? "border-accent/40 bg-accent/5" : "border-amber/30 bg-amber/5"
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className={`h-5 w-5 ${isRunning ? "text-accent animate-pulse" : "text-amber"}`} />
                <p className="font-display text-sm font-bold text-primary">
                  {isRunning ? "Execução em Andamento" : "Ingestão concluída — Normalizando"}
                </p>
              </div>
              {liveElapsedStr && (
                <span className="font-mono text-sm font-bold text-accent tabular-nums">{liveElapsedStr}</span>
              )}
            </div>

            {/* Phase pipeline strip */}
            <div className="flex items-stretch gap-1">
              <div className={`flex-1 rounded-lg border px-4 py-3 ${
                currentPhase === "ingest" ? "border-accent/40 bg-accent/10" :
                currentPhase === "error" ? "border-red-500/30 bg-red-500/5" :
                "border-success/30 bg-success/5"
              }`}>
                <div className="flex items-center gap-1.5 mb-1">
                  {currentPhase === "ingest" && <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />}
                  {currentPhase !== "ingest" && currentPhase !== "error" && <span className="h-2 w-2 rounded-full bg-success" />}
                  {currentPhase === "error" && <span className="h-2 w-2 rounded-full bg-red-500" />}
                  <p className={`font-mono text-xs font-bold uppercase ${
                    currentPhase === "ingest" ? "text-accent" :
                    currentPhase === "error" ? "text-red-400" : "text-success"
                  }`}>Ingestão</p>
                </div>
                <p className="font-mono text-[10px] text-secondary">
                  {detail.run.items_fetched.toLocaleString("pt-BR")} coletados
                </p>
                {isRunning && (
                  <div className="mt-1.5 h-1 rounded-full bg-surface-subtle overflow-hidden">
                    <div className="h-full w-full rounded-full bg-accent animate-pulse" />
                  </div>
                )}
              </div>
              <div className="flex items-center px-1 text-muted">→</div>
              <div className={`flex-1 rounded-lg border px-4 py-3 ${
                currentPhase === "normalize" ? "border-accent/40 bg-accent/10" :
                currentPhase === "done" ? "border-success/30 bg-success/5" :
                "border-border bg-surface-subtle"
              }`}>
                <div className="flex items-center gap-1.5 mb-1">
                  {currentPhase === "normalize" && <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />}
                  {currentPhase === "done" && <span className="h-2 w-2 rounded-full bg-success" />}
                  {currentPhase !== "normalize" && currentPhase !== "done" && <span className="h-2 w-2 rounded-full bg-muted/40" />}
                  <p className={`font-mono text-xs font-bold uppercase ${
                    currentPhase === "normalize" ? "text-accent" :
                    currentPhase === "done" ? "text-success" : "text-muted"
                  }`}>Normalização</p>
                </div>
                <p className="font-mono text-[10px] text-secondary">
                  {currentPhase === "ingest" ? "Aguardando ingestão" :
                   `${detail.run.items_normalized.toLocaleString("pt-BR")} (${normalizedPct}%)`}
                </p>
                {currentPhase === "normalize" && detail.run.items_fetched > 0 && (
                  <div className="mt-1.5 h-1 rounded-full bg-surface-subtle overflow-hidden">
                    <div className="h-full rounded-full bg-success transition-all duration-500" style={{ width: `${normalizedPct}%` }} />
                  </div>
                )}
              </div>
            </div>

            {/* Live metrics grid */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {detail.run.cursor_info && (
                <div className="rounded-lg border border-border bg-surface-card px-3 py-2">
                  <div className="flex items-center gap-1 mb-0.5">
                    <MapPin className="h-3 w-3 text-accent" />
                    <p className="font-mono text-[9px] uppercase tracking-wide text-muted">Posição</p>
                  </div>
                  <p className="font-mono text-xs font-bold text-primary">{detail.run.cursor_info}</p>
                </div>
              )}
              {detail.run.rate_per_min != null && detail.run.rate_per_min > 0 && (
                <div className="rounded-lg border border-border bg-surface-card px-3 py-2">
                  <div className="flex items-center gap-1 mb-0.5">
                    <Zap className="h-3 w-3 text-accent" />
                    <p className="font-mono text-[9px] uppercase tracking-wide text-muted">Velocidade</p>
                  </div>
                  <p className="font-mono text-xs font-bold text-primary">~{Math.round(detail.run.rate_per_min).toLocaleString("pt-BR")}/min</p>
                </div>
              )}
              {detail.run.pages_fetched != null && detail.run.pages_fetched > 0 && (
                <div className="rounded-lg border border-border bg-surface-card px-3 py-2">
                  <div className="flex items-center gap-1 mb-0.5">
                    <FileText className="h-3 w-3 text-accent" />
                    <p className="font-mono text-[9px] uppercase tracking-wide text-muted">Páginas</p>
                  </div>
                  <p className="font-mono text-xs font-bold text-primary">{detail.run.pages_fetched.toLocaleString("pt-BR")}</p>
                </div>
              )}
              {detail.run.cursor_end && (
                <div className="rounded-lg border border-border bg-surface-card px-3 py-2">
                  <div className="flex items-center gap-1 mb-0.5">
                    <Database className="h-3 w-3 text-accent" />
                    <p className="font-mono text-[9px] uppercase tracking-wide text-muted">Cursor</p>
                  </div>
                  <p className="font-mono text-[10px] font-bold text-primary break-all">{detail.run.cursor_end}</p>
                </div>
              )}
            </div>

            <p className="font-mono text-[10px] text-muted">
              {isRunning
                ? "Dados atualizados a cada 5 segundos automaticamente."
                : "A ingestão foi concluída. A normalização processa os dados brutos em eventos estruturados."}
            </p>
          </section>
        )}

        {/* ── KPI strip ────────────────────────────────────────── */}
        <section>
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted mb-3">Métricas da Execução</p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <KpiCard
              icon={Database}
              label={isRunning ? "Coletados até agora" : "Itens Coletados"}
              value={detail.run.items_fetched}
              sub={isRunning && detail.run.cursor_info ? detail.run.cursor_info : undefined}
            />
            <KpiCard
              icon={ArrowDownUp}
              label="Itens Normalizados"
              value={detail.run.items_normalized}
              sub={`${normalizedPct}% do total coletado`}
            />
            <KpiCard
              icon={Hash}
              label="Registros Persistidos"
              value={detail.summary.records_stored}
              sub={`${normalizedPct}% normalizado com sucesso`}
            />
            <KpiCard
              icon={Copy}
              label="Duplicidades"
              value={detail.summary.duplicate_raw_ids}
              sub={dupPct > 0 ? `${dupPct}% do total` : "Nenhuma duplicidade"}
            />
          </div>
        </section>

        {/* ── Timeline ─────────────────────────────────────────── */}
        <section>
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted mb-3">Linha do Tempo</p>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-border bg-surface-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Clock className="h-4 w-4 text-accent" />
                <p className="font-mono text-[10px] uppercase tracking-widest text-muted">Execução</p>
              </div>
              <div className="space-y-2.5">
                {[
                  { label: "Início",   value: fmtDate(detail.run.started_at)  },
                  { label: "Fim",      value: fmtDate(detail.run.finished_at) },
                  { label: "Duração",  value: isRunning && liveElapsedStr ? liveElapsedStr : duration },
                ].map((row) => (
                  <div key={row.label} className="flex items-center justify-between text-xs">
                    <span className="text-muted">{row.label}</span>
                    <span className="font-mono font-semibold text-primary tabular-nums">{row.value}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-border bg-surface-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <BarChart3 className="h-4 w-4 text-accent" />
                <p className="font-mono text-[10px] uppercase tracking-widest text-muted">Registros</p>
              </div>
              <div className="space-y-2.5">
                {[
                  { label: "Registro mais antigo",  value: fmtDate(detail.summary.first_record_at) },
                  { label: "Registro mais recente", value: fmtDate(detail.summary.last_record_at)  },
                  ...(detail.run.cursor_info ? [{ label: "Posição atual", value: detail.run.cursor_info }] : []),
                  ...(detail.run.cursor_end ? [{ label: "Cursor técnico", value: detail.run.cursor_end }] : []),
                ].map((row) => (
                  <div key={row.label} className="flex items-center justify-between text-xs">
                    <span className="text-muted">{row.label}</span>
                    <span className="font-mono font-semibold text-primary tabular-nums">{row.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ── Errors ───────────────────────────────────────────── */}
        {detail.run.errors && (() => {
          // Filter out internal metadata keys (_progress, yielded)
          const displayErrors = Object.fromEntries(
            Object.entries(detail.run.errors).filter(([k]) => !k.startsWith("_") && k !== "yielded")
          );
          if (Object.keys(displayErrors).length === 0) return null;
          const isPartial = (detail.run.errors as Record<string, unknown>).partial === true;
          const isRetryable = (detail.run.errors as Record<string, unknown>).retryable === true;
          return isPartial ? (
            <section className="rounded-xl border border-amber/20 bg-amber/5 p-5">
              <div className="flex items-center gap-2 mb-1">
                <AlertTriangle className="h-4 w-4 text-amber" />
                <p className="font-mono text-[10px] uppercase tracking-widest text-amber">Interrupção Parcial</p>
              </div>
              <p className="text-xs text-secondary mb-3">
                A execução foi interrompida por timeout da API externa, mas todos os itens buscados foram normalizados com sucesso.
                O próximo ciclo retomará automaticamente a partir do cursor salvo.
              </p>
              <pre className="max-h-40 overflow-auto rounded-lg bg-surface-card border border-border p-3 font-mono text-xs text-secondary leading-relaxed">
                {stringifyJson(displayErrors)}
              </pre>
            </section>
          ) : isRetryable ? (
            <section className="rounded-xl border border-amber/20 bg-amber/5 p-5">
              <div className="flex items-center gap-2 mb-1">
                <AlertTriangle className="h-4 w-4 text-amber" />
                <p className="font-mono text-[10px] uppercase tracking-widest text-amber">Falha na API Externa</p>
              </div>
              <p className="text-xs text-secondary mb-3">
                A API governamental retornou um erro temporário (timeout ou indisponibilidade). Não há falha no sistema OpenWatch.
                A execução será retomada automaticamente no próximo ciclo.
              </p>
              <pre className="max-h-40 overflow-auto rounded-lg bg-surface-card border border-border p-3 font-mono text-xs text-secondary leading-relaxed">
                {stringifyJson(displayErrors)}
              </pre>
            </section>
          ) : (
            <section className="rounded-xl border border-error/20 bg-error/5 p-5">
              <div className="flex items-center gap-2 mb-3">
                <CircleX className="h-4 w-4 text-error" />
                <p className="font-mono text-[10px] uppercase tracking-widest text-error">Erros Registrados</p>
              </div>
              <pre className="max-h-40 overflow-auto rounded-lg bg-error/10 border border-error/20 p-3 font-mono text-xs text-error leading-relaxed">
                {stringifyJson(displayErrors)}
              </pre>
            </section>
          );
        })()}

        {/* ── Field profile ─────────────────────────────────────── */}
        {detail.field_profile.length > 0 && (
          <section className="rounded-xl border border-border bg-surface-card overflow-hidden">
            <button
              type="button"
              onClick={() => setFieldProfileOpen((o) => !o)}
              className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left hover:bg-surface-subtle/50 transition-colors"
            >
              <div className="flex items-center gap-2.5">
                <Braces className="h-4 w-4 text-accent" />
                <div>
                  <p className="font-display text-sm font-bold text-primary">
                    Perfil dos Campos
                    <span className="ml-2 font-mono text-xs font-normal text-muted">({detail.field_profile.length})</span>
                  </p>
                  <p className="font-mono text-[10px] text-muted mt-0.5">
                    Presença e tipos de cada campo — {detail.summary.profile_sampled_records} registros amostrados
                  </p>
                </div>
              </div>
              {fieldProfileOpen ? <ChevronUp className="h-4 w-4 shrink-0 text-muted" /> : <ChevronDown className="h-4 w-4 shrink-0 text-muted" />}
            </button>

            {fieldProfileOpen && (
              <div className="border-t border-border">
                <div className="overflow-x-auto">
                  <table className="w-full text-left">
                    <thead className="bg-surface-base border-b border-border">
                      <tr>
                        {["Campo", "Cobertura", "Tipo(s)", "Exemplos"].map((h) => (
                          <th key={h} className="px-4 py-2.5 font-mono text-[9px] uppercase tracking-widest text-muted">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {detail.field_profile.map((field, idx) => (
                        <FieldProfileRow
                          key={`${idx}-${field.key}`}
                          field={field}
                          total={detail.summary.profile_sampled_records}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="border-t border-border px-5 py-3 bg-surface-base">
                  <p className="font-mono text-[10px] text-muted">
                    Cobertura: verde ≥90%, amarelo ≥50%, vermelho &lt;50% · Amostrado sobre {detail.summary.profile_sampled_records}/{detail.summary.profile_sample_limit} registros
                    {detail.job.supports_incremental && " · Job suporta ingestão incremental"}
                  </p>
                </div>
              </div>
            )}
          </section>
        )}

        {/* ── Samples ──────────────────────────────────────────── */}
        <section className="rounded-xl border border-border bg-surface-card overflow-hidden">
          <button
            type="button"
            onClick={() => setSamplesOpen((o) => !o)}
            className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left hover:bg-surface-subtle/50 transition-colors"
          >
            <div className="flex items-center gap-2.5">
              <FileJson className="h-4 w-4 text-accent" />
              <div>
                <p className="font-display text-sm font-bold text-primary">
                  Amostra de Registros
                  <span className="ml-2 font-mono text-xs font-normal text-muted">({detail.samples.length})</span>
                </p>
                <p className="font-mono text-[10px] text-muted mt-0.5">
                  Registros reais para auditoria e verificação de qualidade
                </p>
              </div>
            </div>
            {samplesOpen ? <ChevronUp className="h-4 w-4 shrink-0 text-muted" /> : <ChevronDown className="h-4 w-4 shrink-0 text-muted" />}
          </button>

          {samplesOpen && (
            <div className="border-t border-border px-5 pb-5 pt-4">
              {detail.samples.length === 0 ? (
                <div className="flex flex-col items-center justify-center rounded-xl border border-border bg-surface-base py-10 gap-2">
                  <FileText className="h-7 w-7 text-muted" />
                  <p className="text-sm text-muted">Nenhum registro bruto encontrado para esta execução.</p>
                </div>
              ) : (
                <>
                  <div className="space-y-3">
                    {pagedSamples.map((sample, localIndex) => {
                      const gIdx = globalOffset + localIndex;
                      const isOpen = openSamples.has(gIdx);
                      return (
                        <article key={sample.raw_id} className="rounded-xl border border-border bg-surface-base p-4">
                          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                            <div className="flex items-center gap-2">
                              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-accent-subtle border border-accent/20 font-mono text-[10px] font-bold text-accent">
                                {gIdx + 1}
                              </span>
                              <code className="font-mono text-xs font-bold text-primary">{sample.raw_id}</code>
                            </div>
                            <span className="font-mono text-[10px] text-muted tabular-nums">
                              {fmtDate(sample.created_at)}
                            </span>
                          </div>

                          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                            {Object.entries(sample.preview).map(([key, value]) => {
                              const display = typeof value === "string" ? value : stringifyJson(value);
                              const isBlock = shouldRenderAsBlock(display);
                              return (
                                <div key={`${sample.raw_id}-${key}`} className="rounded-lg border border-border bg-surface-card px-3 py-2">
                                  <p className="font-mono text-[9px] uppercase tracking-widest text-muted mb-1">{key}</p>
                                  {isBlock ? (
                                    <pre className="max-h-36 overflow-auto font-mono text-[10px] leading-relaxed text-secondary whitespace-pre-wrap break-words">
                                      {display}
                                    </pre>
                                  ) : (
                                    <p className="text-xs text-secondary break-words">{display}</p>
                                  )}
                                </div>
                              );
                            })}
                          </div>

                          <details
                            className="mt-3 rounded-xl border border-border overflow-hidden"
                            open={isOpen}
                            onToggle={(e) => {
                              const next = new Set(openSamples);
                              (e.currentTarget as HTMLDetailsElement).open ? next.add(gIdx) : next.delete(gIdx);
                              setOpenSamples(next);
                            }}
                          >
                            <summary className="cursor-pointer bg-surface-base px-4 py-2 font-mono text-[10px] uppercase tracking-widest text-muted hover:text-primary transition-colors">
                              Ver JSON bruto original
                            </summary>
                            <pre className="max-h-72 overflow-auto border-t border-border bg-surface-card p-4 font-mono text-[11px] text-secondary leading-relaxed">
                              {stringifyJson(sample.raw_data)}
                            </pre>
                          </details>
                        </article>
                      );
                    })}
                  </div>

                  {totalSamplePages > 1 && (
                    <div className="mt-4 flex items-center justify-between border-t border-border pt-4">
                      <p className="font-mono text-[11px] tabular-nums text-muted">
                        {globalOffset + 1}–{Math.min(globalOffset + SAMPLES_PER_PAGE, detail.samples.length)} de {detail.samples.length} registros
                      </p>
                      <div className="flex items-center gap-1.5">
                        <button
                          disabled={samplesPage === 0}
                          onClick={() => setSamplesPage((p) => p - 1)}
                          className="rounded-lg border border-border bg-surface-card px-3 py-1.5 text-xs font-semibold text-secondary hover:text-primary hover:bg-surface-subtle disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        >
                          Anterior
                        </button>
                        <span className="font-mono text-xs text-muted tabular-nums px-2">
                          {samplesPage + 1} / {totalSamplePages}
                        </span>
                        <button
                          disabled={samplesPage === totalSamplePages - 1}
                          onClick={() => setSamplesPage((p) => p + 1)}
                          className="rounded-lg border border-border bg-surface-card px-3 py-1.5 text-xs font-semibold text-secondary hover:text-primary hover:bg-surface-subtle disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        >
                          Próximo
                        </button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </section>

        {/* ── Legal footer ─────────────────────────────────────── */}
        <div className="rounded-xl border border-border bg-surface-base px-5 py-4">
          <p className="font-mono text-[10px] text-muted leading-relaxed">
            <strong className="font-semibold text-secondary">Transparência:</strong>{" "}
            Esta página exibe o detalhe técnico de uma execução de ingestão de dados públicos.
            Os registros são obtidos exclusivamente de fontes oficiais e tratados com deduplicação automática.
            Nenhum dado pessoal é coletado além do estritamente necessário (LGPD art. 7, VII).
          </p>
        </div>
      </div>
    </div>
  );
}
