"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getIngestRunDetail } from "@/lib/api";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { DetailSkeleton } from "@/components/Skeleton";
import { EmptyState } from "@/components/EmptyState";
import { formatDateTime, formatNumber } from "@/lib/utils";
import type { IngestRunDetailResponse, IngestRunFieldProfile } from "@/lib/types";
import {
  Database,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Clock,
  CircleX,
  FileJson,
  Braces,
  Network,
  Layers,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Timer,
  HelpCircle,
  ArrowLeft,
  Copy,
  Info,
  BarChart3,
  Hash,
  FileText,
  ArrowDownUp,
} from "lucide-react";

/* ── Status helpers ────────────────────────────────────────────── */

const STATUS_CONFIG: Record<string, { label: string; cls: string; Icon: typeof CheckCircle2; desc: string }> = {
  completed: {
    label: "Concluído",
    cls: "status-ok",
    Icon: CheckCircle2,
    desc: "A execução foi finalizada com sucesso. Todos os registros foram processados.",
  },
  running: {
    label: "Em execução",
    cls: "status-pending",
    Icon: Loader2,
    desc: "Esta execução ainda está em andamento. Os números podem mudar.",
  },
  error: {
    label: "Erro",
    cls: "status-error",
    Icon: CircleX,
    desc: "A execução encontrou um erro durante o processamento.",
  },
};

function getStatusConfig(status: string) {
  return STATUS_CONFIG[status] ?? {
    label: status,
    cls: "bg-surface-subtle text-secondary border-border",
    Icon: Clock,
    desc: "Status aguardando atualização.",
  };
}

/* ── Formatting helpers ────────────────────────────────────────── */

function fmtMaybeDate(value?: string | null): string {
  if (!value) return "—";
  return formatDateTime(value);
}

function pct(value: number, total: number): number {
  if (total <= 0) return 0;
  return Math.round((value / total) * 10000) / 100;
}

function formatDuration(startedAt?: string | null, finishedAt?: string | null): string {
  if (!startedAt) return "—";
  const start = new Date(startedAt).getTime();
  const end = finishedAt ? new Date(finishedAt).getTime() : Date.now();
  const ms = end - start;
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  const minutes = Math.floor(ms / 60_000);
  const seconds = Math.round((ms % 60_000) / 1000);
  return `${minutes}min ${seconds}s`;
}

function stringifyJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function shouldRenderAsBlock(value: unknown): boolean {
  if (typeof value !== "string") return true;
  const trimmed = value.trim();
  return trimmed.startsWith("{") || trimmed.startsWith("[") || trimmed.includes("\n");
}

function formatStructuredValue(value: unknown): string {
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
      try {
        return JSON.stringify(JSON.parse(trimmed), null, 2);
      } catch {
        return value;
      }
    }
    return value;
  }
  return stringifyJson(value);
}

function coverageColor(pctValue: number): string {
  if (pctValue >= 90) return "bg-success";
  if (pctValue >= 70) return "bg-success/70";
  if (pctValue >= 50) return "bg-amber";
  return "bg-error";
}

/* ── KPI Card ──────────────────────────────────────────────────── */

function KpiCard({
  label,
  value,
  sub,
  icon: Icon,
  tooltip,
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: typeof Database;
  tooltip: string;
}) {
  return (
    <div className="metric-card">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-muted">{label}</p>
        <span className="group relative">
          <HelpCircle className="h-3.5 w-3.5 text-placeholder transition hover:text-muted" />
          <span className="pointer-events-none absolute bottom-full right-0 z-10 mb-1 hidden w-56 rounded-lg bg-primary px-3 py-2 text-xs font-normal text-surface-card group-hover:block">
            {tooltip}
          </span>
        </span>
      </div>
      <div className="mt-2 flex items-end gap-2">
        <Icon className="h-5 w-5 text-accent" />
        <p className="text-2xl font-bold tracking-tight text-primary">
          {typeof value === "number" ? formatNumber(value) : value}
        </p>
      </div>
      {sub && <p className="mt-1 text-xs text-muted">{sub}</p>}
    </div>
  );
}

/* ── Field Profile Row ─────────────────────────────────────────── */

function FieldProfileRow({ field, total }: { field: IngestRunFieldProfile; total: number }) {
  const coverage = field.coverage_pct;
  return (
    <tr className="border-b border-border last:border-0">
      <td className="px-3 py-2.5 align-top">
        <code className="rounded bg-surface-subtle px-1.5 py-0.5 font-mono text-xs text-primary">
          {field.key}
        </code>
      </td>
      <td className="px-3 py-2.5 align-top">
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-16 rounded-full bg-surface-hover">
            <div
              className={`h-1.5 rounded-full transition-all ${coverageColor(coverage)}`}
              style={{ width: `${Math.min(coverage, 100)}%` }}
            />
          </div>
          <span className="text-xs font-medium text-secondary">
            {coverage}%
          </span>
          <span className="text-xs text-muted">
            ({field.present_count}/{total})
          </span>
        </div>
      </td>
      <td className="px-3 py-2.5 align-top">
        <div className="flex flex-wrap gap-1">
          {field.detected_types.map((t) => (
            <span key={t} className="rounded bg-accent-subtle px-1.5 py-0.5 text-xs text-accent">
              {t}
            </span>
          ))}
        </div>
      </td>
      <td className="px-3 py-2.5 align-top">
        <div className="space-y-1.5">
          {field.examples.length === 0 ? (
            <span className="text-xs text-muted">Sem exemplos</span>
          ) : (
            field.examples.map((example, index) => {
              const displayValue = formatStructuredValue(example);
              const blockRender = shouldRenderAsBlock(displayValue);
              if (blockRender) {
                return (
                  <pre
                    key={`${field.key}-${index}`}
                    className="max-h-36 overflow-auto rounded-md border border-border bg-surface-base px-2 py-1.5 font-mono text-[11px] leading-relaxed whitespace-pre-wrap break-words"
                  >
                    {displayValue}
                  </pre>
                );
              }
              return (
                <p
                  key={`${field.key}-${index}`}
                  className="rounded-md border border-border bg-surface-base px-2 py-1.5 text-xs text-secondary break-words"
                >
                  {displayValue}
                </p>
              );
            })
          )}
        </div>
      </td>
    </tr>
  );
}

/* ── Main Page ─────────────────────────────────────────────────── */

const SAMPLES_PER_PAGE = 10;

export default function CoverageRunDetailPage() {
  const params = useParams<{ id: string }>();
  const runId = params.id;

  const [detail, setDetail] = useState<IngestRunDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openSamples, setOpenSamples] = useState<Set<number>>(() => new Set());
  const [samplesPage, setSamplesPage] = useState(0);
  const [fieldProfileOpen, setFieldProfileOpen] = useState(true);
  const [samplesSectionOpen, setSamplesSectionOpen] = useState(false);

  const fetchDetail = () => {
    if (!runId) return;
    setLoading(true);
    setError(null);
    getIngestRunDetail(runId)
      .then(setDetail)
      .catch(() => setError("Não foi possível carregar o detalhe da execução."))
      .finally(() => setLoading(false));
  };

  useEffect(fetchDetail, [runId]);

  const normalizedPct = useMemo(() => {
    if (!detail) return 0;
    return pct(detail.run.items_normalized, detail.run.items_fetched);
  }, [detail]);

  const dupPct = useMemo(() => {
    if (!detail || detail.summary.records_stored === 0) return 0;
    return pct(detail.summary.duplicate_raw_ids, detail.summary.records_stored);
  }, [detail]);

  /* ── Loading ────────────────────────────────────────────────── */
  if (loading) {
    return (
      <div className="page-wrap">
        <PageHeader
          title="Detalhe da Execução"
          breadcrumbs={[{ label: "Cobertura", href: "/coverage" }, { label: "Detalhe" }]}
        />
        <div className="mt-4">
          <DetailSkeleton />
        </div>
      </div>
    );
  }

  /* ── Error ──────────────────────────────────────────────────── */
  if (error || !detail) {
    return (
      <div className="page-wrap">
        <PageHeader
          title="Detalhe da Execução"
          breadcrumbs={[{ label: "Cobertura", href: "/coverage" }, { label: "Detalhe" }]}
        />
        <div className="mt-6">
          <EmptyState
            icon={AlertTriangle}
            title="Erro ao carregar execução"
            description={error ?? "Detalhe da execução indisponível."}
          />
          <div className="mt-4 text-center">
            <Button onClick={fetchDetail}>
              <RefreshCw className="h-4 w-4" />
              Tentar novamente
            </Button>
          </div>
        </div>
      </div>
    );
  }

  /* ── Status config ──────────────────────────────────────────── */
  const statusCfg = getStatusConfig(detail.run.status);
  const duration = formatDuration(detail.run.started_at, detail.run.finished_at);

  /* ── Samples pagination ─────────────────────────────────────── */
  const totalPages = Math.ceil(detail.samples.length / SAMPLES_PER_PAGE);
  const pagedSamples = detail.samples.slice(
    samplesPage * SAMPLES_PER_PAGE,
    (samplesPage + 1) * SAMPLES_PER_PAGE,
  );
  const globalOffset = samplesPage * SAMPLES_PER_PAGE;

  return (
    <div className="page-wrap">
      <PageHeader
        title={`${detail.run.connector} / ${detail.run.job}`}
        breadcrumbs={[{ label: "Cobertura", href: "/coverage" }, { label: "Detalhe" }]}
      />

      {/* Back link */}
      <Link
        href="/coverage"
        className="mt-3 inline-flex items-center gap-1 rounded-md px-1 py-0.5 text-xs text-muted transition hover:bg-surface-subtle hover:text-accent"
      >
        <ArrowLeft className="h-3 w-3" />
        Voltar para Cobertura
      </Link>

      {/* ── Header ─────────────────────────────────────────────── */}
      <section className="surface-card mt-4 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent-subtle">
                <Database className="h-5 w-5 text-accent" />
              </div>
              <div>
                <h1 className="font-display text-xl font-bold tracking-tight text-primary">
                  {detail.run.connector} / {detail.run.job}
                </h1>
                {detail.job.domain && (
                  <span className="mt-0.5 inline-block rounded bg-surface-subtle px-1.5 py-0.5 text-xs text-secondary">
                    Domínio: {detail.job.domain}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs text-muted">
              <Timer className="h-3.5 w-3.5" />
              {duration}
            </div>
            <span
              className={`inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-semibold ${statusCfg.cls}`}
            >
              <statusCfg.Icon
                className={`h-3.5 w-3.5 ${detail.run.status === "running" ? "animate-spin" : ""}`}
              />
              {statusCfg.label}
            </span>
          </div>
        </div>

        {/* Status explanation */}
        <div className="mt-3 flex items-start gap-2 rounded-md bg-surface-base/80 px-3 py-2">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
          <p className="text-xs text-secondary">{statusCfg.desc}</p>
        </div>

        {/* Job description */}
        {detail.job.description && (
          <p className="mt-3 text-sm text-secondary">{detail.job.description}</p>
        )}
      </section>

      {/* ── KPI Grid ───────────────────────────────────────────── */}
      <section className="surface-card mt-6 p-4">
        <div className="mb-3 flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-accent" />
          <h2 className="panel-title">Números da execução</h2>
        </div>
        <p className="text-xs text-muted">
          Métricas quantitativas do processamento para validar volume, normalização e persistência.
        </p>

        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <KpiCard
            icon={Database}
            label="Itens Buscados"
            value={detail.run.items_fetched}
            tooltip="Quantidade de registros brutos recuperados da fonte de dados original durante esta execução."
          />
          <KpiCard
            icon={ArrowDownUp}
            label="Itens Normalizados"
            value={detail.run.items_normalized}
            sub={`${normalizedPct}% do total buscado`}
            tooltip="Registros que foram convertidos para o formato padrão da plataforma. Uma taxa abaixo de 100% pode indicar registros com formato inesperado."
          />
          <KpiCard
            icon={Hash}
            label="Registros Persistidos"
            value={detail.summary.records_stored}
            sub={`${formatNumber(detail.summary.distinct_raw_ids)} IDs únicos`}
            tooltip="Total de registros salvos no banco de dados. IDs únicos indica quantos registros distintos foram identificados."
          />
          <KpiCard
            icon={Copy}
            label="Duplicidades Detectadas"
            value={detail.summary.duplicate_raw_ids}
            sub={dupPct > 0 ? `${dupPct}% do total` : "Nenhuma duplicidade"}
            tooltip="Registros que já existiam no banco de dados. Um número alto indica atualizações incrementais (normal) ou reprocessamento."
          />
        </div>
      </section>

      {/* ── Timeline ───────────────────────────────────────────── */}
      <section className="surface-card mt-6 p-4">
        <h2 className="panel-title">Linha do tempo</h2>
        <p className="mt-1 text-xs text-muted">
          Janela temporal da execução e dos registros processados.
        </p>

        <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
          <div className="rounded-lg border border-border bg-surface-card p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">
              Execução
            </h3>
            <div className="mt-2 space-y-2 text-sm text-secondary">
              <div className="flex justify-between">
                <span className="text-muted">Início</span>
                <span className="font-medium">{fmtMaybeDate(detail.run.started_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">Fim</span>
                <span className="font-medium">{fmtMaybeDate(detail.run.finished_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">Duração</span>
                <span className="font-medium">{duration}</span>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-border bg-surface-card p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">
              Registros
            </h3>
            <div className="mt-2 space-y-2 text-sm text-secondary">
              <div className="flex justify-between">
                <span className="text-muted">Registro mais antigo</span>
                <span className="font-medium">{fmtMaybeDate(detail.summary.first_record_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">Registro mais recente</span>
                <span className="font-medium">{fmtMaybeDate(detail.summary.last_record_at)}</span>
              </div>
              {detail.run.cursor_start && (
                <div className="flex justify-between">
                  <span className="text-muted">Cursor inicio</span>
                  <span className="font-mono text-xs font-medium">{detail.run.cursor_start}</span>
                </div>
              )}
              {detail.run.cursor_end && (
                <div className="flex justify-between">
                  <span className="text-muted">Cursor fim</span>
                  <span className="font-mono text-xs font-medium">{detail.run.cursor_end}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ── How it works ───────────────────────────────────────── */}
      <section className="mt-6 rounded-xl border border-accent/20 bg-accent-subtle/40 p-4">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-primary">
          <Info className="h-4 w-4 text-accent" />
          Como funciona este processamento?
        </h2>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="flex items-start gap-2">
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-subtle text-xs font-bold text-accent">
              1
            </div>
            <div>
              <p className="text-xs font-semibold text-primary">Ingestão</p>
              <p className="text-xs text-secondary">
                O conector acessa a fonte pública e baixa os registros brutos (payloads JSON).
              </p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-subtle text-xs font-bold text-accent">
              2
            </div>
            <div>
              <p className="text-xs font-semibold text-primary">Normalização</p>
              <p className="text-xs text-secondary">
                Os registros são convertidos para o formato padrão, extraindo campos-chave.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-subtle text-xs font-bold text-accent">
              3
            </div>
            <div>
              <p className="text-xs font-semibold text-primary">Persistência</p>
              <p className="text-xs text-secondary">
                Registros únicos são salvos; duplicatas são detectadas automaticamente pelo ID.
              </p>
            </div>
          </div>
        </div>
        <p className="mt-3 text-xs text-muted">
          O perfil de campos abaixo foi calculado sobre{" "}
          <strong>{detail.summary.profile_sampled_records}</strong> registro(s) desta execução
          (limite técnico: {detail.summary.profile_sample_limit}).
          {detail.job.supports_incremental && (
            <> Este job suporta ingestão incremental — apenas registros novos são processados a cada execução.</>
          )}
        </p>
      </section>

      {/* ── Errors (if any) ────────────────────────────────────── */}
      {detail.run.errors && Object.keys(detail.run.errors).length > 0 && (
        <section className="mt-6 rounded-xl border border-error/20 bg-error-subtle p-4">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-error">
            <CircleX className="h-4 w-4" />
            Erros registrados
          </h2>
          <pre className="mt-2 max-h-40 overflow-auto rounded-md bg-surface-card p-3 font-mono text-xs text-error">
            {stringifyJson(detail.run.errors)}
          </pre>
        </section>
      )}

      {/* ── Field Profile ──────────────────────────────────────── */}
      {detail.field_profile.length > 0 && (
        <section className="surface-card mt-6">
          <button
            type="button"
            onClick={() => setFieldProfileOpen((o) => !o)}
            className="flex w-full items-center justify-between gap-3 p-5 text-left"
          >
            <div>
              <h2 className="flex items-center gap-2 text-lg font-semibold text-primary">
                <Braces className="h-5 w-5 text-accent" />
                Perfil dos Campos ({detail.field_profile.length})
              </h2>
              <p className="mt-1 text-xs text-muted">
                Presença e tipos de cada campo encontrado nos registros brutos.
                A barra de cobertura indica em quantos registros o campo aparece.
              </p>
            </div>
            {fieldProfileOpen ? (
              <ChevronUp className="h-5 w-5 shrink-0 text-muted" />
            ) : (
              <ChevronDown className="h-5 w-5 shrink-0 text-muted" />
            )}
          </button>

          {fieldProfileOpen && (
            <div className="border-t border-border px-5 pb-5 pt-3">
              <div className="overflow-x-auto rounded-lg border border-border">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-border bg-surface-base">
                    <tr>
                      <th className="px-3 py-2 text-xs font-semibold text-secondary">
                        Campo
                      </th>
                      <th className="px-3 py-2 text-xs font-semibold text-secondary">
                        Cobertura
                      </th>
                      <th className="px-3 py-2 text-xs font-semibold text-secondary">
                        Tipo(s)
                      </th>
                      <th className="px-3 py-2 text-xs font-semibold text-secondary">
                        Exemplos
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.field_profile.map((field) => (
                      <FieldProfileRow
                        key={field.key}
                        field={field}
                        total={detail.summary.profile_sampled_records}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-2 text-xs text-muted">
                Cobertura indica a proporção de registros amostrados que possuem este campo preenchido.
                Verde ({"\u2265"}90%), amarelo (50-89%), vermelho ({"<"}50%).
              </p>
            </div>
          )}
        </section>
      )}

      {/* ── Samples ────────────────────────────────────────────── */}
      <section className="surface-card mt-6">
        <button
          type="button"
          onClick={() => setSamplesSectionOpen((o) => !o)}
          className="flex w-full items-center justify-between gap-3 p-5 text-left"
        >
          <div>
            <h2 className="flex items-center gap-2 text-lg font-semibold text-primary">
              <FileJson className="h-5 w-5 text-accent" />
              Amostra de Registros ({detail.samples.length})
            </h2>
            <p className="mt-1 text-xs text-muted">
              Registros reais processados nesta execução, exibidos para auditoria e verificação.
              Cada registro mostra os principais campos e permite ver o JSON bruto original.
            </p>
          </div>
          {samplesSectionOpen ? (
            <ChevronUp className="h-5 w-5 shrink-0 text-muted" />
          ) : (
            <ChevronDown className="h-5 w-5 shrink-0 text-muted" />
          )}
        </button>

        {samplesSectionOpen && (
          <div className="border-t border-border px-5 pb-5 pt-3">
            {detail.samples.length === 0 ? (
              <div className="rounded-lg border border-border bg-surface-base p-6 text-center">
                <FileText className="mx-auto h-8 w-8 text-placeholder" />
                <p className="mt-2 text-sm text-muted">
                  Nenhum registro bruto encontrado para esta execução.
                </p>
              </div>
            ) : (
              <>
                <div className="space-y-3">
                  {pagedSamples.map((sample, localIndex) => {
                    const gIdx = globalOffset + localIndex;
                    const isOpen = openSamples.has(gIdx);

                    return (
                      <article
                        key={sample.raw_id}
                        className="rounded-lg border border-border bg-surface-card p-4"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className="flex h-6 w-6 items-center justify-center rounded bg-surface-subtle text-xs font-bold text-secondary">
                              {gIdx + 1}
                            </span>
                            <p className="font-mono text-xs font-semibold text-primary">
                              {sample.raw_id}
                            </p>
                          </div>
                          <p className="text-xs text-muted">
                            {fmtMaybeDate(sample.created_at)}
                          </p>
                        </div>

                        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                          {Object.entries(sample.preview).map(([key, value]) => {
                            const displayValue =
                              typeof value === "string" ? value : stringifyJson(value);
                            const blockRender = shouldRenderAsBlock(displayValue);
                            return (
                              <div
                                key={`${sample.raw_id}-${key}`}
                                className="rounded-md border border-border bg-surface-base px-2.5 py-2"
                              >
                                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">
                                  {key}
                                </p>
                                {blockRender ? (
                                  <pre className="mt-1 max-h-48 overflow-auto rounded bg-surface-card px-2 py-1.5 font-mono text-[11px] leading-relaxed text-secondary whitespace-pre-wrap break-words">
                                    {displayValue}
                                  </pre>
                                ) : (
                                  <p className="mt-0.5 text-xs text-secondary break-words">
                                    {displayValue}
                                  </p>
                                )}
                              </div>
                            );
                          })}
                        </div>

                        <details
                          className="mt-3 rounded-md border border-border"
                          open={isOpen}
                          onToggle={(e) => {
                            const next = new Set(openSamples);
                            if ((e.currentTarget as HTMLDetailsElement).open) {
                              next.add(gIdx);
                            } else {
                              next.delete(gIdx);
                            }
                            setOpenSamples(next);
                          }}
                        >
                          <summary className="cursor-pointer rounded-t-md bg-surface-base px-3 py-2 text-xs font-medium text-secondary hover:text-primary">
                            Ver JSON bruto original
                          </summary>
                          <pre className="max-h-72 overflow-auto border-t border-border bg-surface-base p-3 text-[11px] text-secondary">
                            {stringifyJson(sample.raw_data)}
                          </pre>
                        </details>
                      </article>
                    );
                  })}
                </div>

                {totalPages > 1 && (
                  <div className="mt-4 flex items-center justify-between">
                    <p className="text-xs text-muted">
                      {globalOffset + 1}–{Math.min(globalOffset + SAMPLES_PER_PAGE, detail.samples.length)} de {detail.samples.length} registros
                    </p>
                    <div className="flex items-center gap-1">
                      <button
                        disabled={samplesPage === 0}
                        onClick={() => setSamplesPage((p) => p - 1)}
                        className="rounded-md border border-border bg-surface-card px-3 py-1.5 text-xs font-medium text-secondary hover:bg-surface-subtle disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        Anterior
                      </button>
                      {totalPages <= 5 ? (
                        Array.from({ length: totalPages }, (_, i) => (
                          <button
                            key={i}
                            onClick={() => setSamplesPage(i)}
                            className={`rounded-md border px-3 py-1.5 text-xs font-medium ${
                              i === samplesPage
                                ? "border-accent bg-accent text-white"
                                : "border-border bg-surface-card text-secondary hover:bg-surface-subtle"
                            }`}
                          >
                            {i + 1}
                          </button>
                        ))
                      ) : (
                        <span className="px-2 text-xs text-muted">
                          {samplesPage + 1} / {totalPages}
                        </span>
                      )}
                      <button
                        disabled={samplesPage === totalPages - 1}
                        onClick={() => setSamplesPage((p) => p + 1)}
                        className="rounded-md border border-border bg-surface-card px-3 py-1.5 text-xs font-medium text-secondary hover:bg-surface-subtle disabled:cursor-not-allowed disabled:opacity-40"
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

      {/* ── Transparency footer ────────────────────────────────── */}
      <div className="surface-muted mt-6 p-3">
        <p className="text-xs text-muted">
          <strong>Transparência:</strong> Esta página exibe o detalhe técnico de uma
          execução de ingestão de dados públicos. Os registros são obtidos exclusivamente
          de fontes oficiais (portais de transparência, APIs públicas) e tratados com
          deduplicação automática. Nenhum dado pessoal é coletado além do estritamente
          necessário para fins de controle social e interesse público (LGPD, art. 7, VII).
        </p>
      </div>
    </div>
  );
}
