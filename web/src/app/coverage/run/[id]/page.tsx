"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getIngestRunDetail } from "@/lib/api";
import { Breadcrumb } from "@/components/Breadcrumb";
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
    label: "Concluido",
    cls: "bg-green-100 text-green-800 border-green-200",
    Icon: CheckCircle2,
    desc: "A execucao foi finalizada com sucesso. Todos os registros foram processados.",
  },
  running: {
    label: "Em execucao",
    cls: "bg-blue-100 text-blue-800 border-blue-200",
    Icon: Loader2,
    desc: "Esta execucao ainda esta em andamento. Os numeros podem mudar.",
  },
  error: {
    label: "Erro",
    cls: "bg-red-100 text-red-800 border-red-200",
    Icon: CircleX,
    desc: "A execucao encontrou um erro durante o processamento.",
  },
};

function getStatusConfig(status: string) {
  return STATUS_CONFIG[status] ?? {
    label: status,
    cls: "bg-gov-gray-100 text-gov-gray-700 border-gov-gray-200",
    Icon: Clock,
    desc: "Status aguardando atualizacao.",
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
  if (pctValue >= 90) return "bg-green-500";
  if (pctValue >= 70) return "bg-emerald-400";
  if (pctValue >= 50) return "bg-amber-400";
  return "bg-red-400";
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
    <div className="rounded-lg border border-gov-gray-200 bg-white p-4">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-gov-gray-500">{label}</p>
        <span className="group relative">
          <HelpCircle className="h-3.5 w-3.5 text-gov-gray-300 transition hover:text-gov-gray-500" />
          <span className="pointer-events-none absolute bottom-full right-0 z-10 mb-1 hidden w-56 rounded-lg bg-gov-gray-900 px-3 py-2 text-xs font-normal text-white shadow-lg group-hover:block">
            {tooltip}
          </span>
        </span>
      </div>
      <div className="mt-2 flex items-end gap-2">
        <Icon className="h-5 w-5 text-gov-blue-500" />
        <p className="text-2xl font-bold tracking-tight text-gov-gray-900">
          {typeof value === "number" ? formatNumber(value) : value}
        </p>
      </div>
      {sub && <p className="mt-1 text-xs text-gov-gray-500">{sub}</p>}
    </div>
  );
}

/* ── Field Profile Row ─────────────────────────────────────────── */

function FieldProfileRow({ field, total }: { field: IngestRunFieldProfile; total: number }) {
  const coverage = field.coverage_pct;
  return (
    <tr className="border-b border-gov-gray-100 last:border-0">
      <td className="px-3 py-2.5 align-top">
        <code className="rounded bg-gov-gray-100 px-1.5 py-0.5 font-mono text-xs text-gov-gray-800">
          {field.key}
        </code>
      </td>
      <td className="px-3 py-2.5 align-top">
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-16 rounded-full bg-gov-gray-200">
            <div
              className={`h-1.5 rounded-full transition-all ${coverageColor(coverage)}`}
              style={{ width: `${Math.min(coverage, 100)}%` }}
            />
          </div>
          <span className="text-xs font-medium text-gov-gray-700">
            {coverage}%
          </span>
          <span className="text-xs text-gov-gray-400">
            ({field.present_count}/{total})
          </span>
        </div>
      </td>
      <td className="px-3 py-2.5 align-top">
        <div className="flex flex-wrap gap-1">
          {field.detected_types.map((t) => (
            <span key={t} className="rounded bg-gov-blue-50 px-1.5 py-0.5 text-xs text-gov-blue-700">
              {t}
            </span>
          ))}
        </div>
      </td>
      <td className="px-3 py-2.5 align-top">
        <div className="space-y-1.5">
          {field.examples.length === 0 ? (
            <span className="text-xs text-gov-gray-400">Sem exemplos</span>
          ) : (
            field.examples.map((example, index) => {
              const displayValue = formatStructuredValue(example);
              const blockRender = shouldRenderAsBlock(displayValue);
              if (blockRender) {
                return (
                  <pre
                    key={`${field.key}-${index}`}
                    className="max-h-36 overflow-auto rounded-md border border-gov-gray-200 bg-gov-gray-50 px-2 py-1.5 font-mono text-[11px] leading-relaxed whitespace-pre-wrap break-words"
                  >
                    {displayValue}
                  </pre>
                );
              }
              return (
                <p
                  key={`${field.key}-${index}`}
                  className="rounded-md border border-gov-gray-200 bg-gov-gray-50 px-2 py-1.5 text-xs text-gov-gray-700 break-words"
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
      .catch(() => setError("Nao foi possivel carregar o detalhe da execucao."))
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
      <div className="mx-auto max-w-5xl px-4 py-8">
        <Breadcrumb
          items={[
            { label: "Cobertura", href: "/coverage" },
            { label: "Detalhe da Execucao" },
          ]}
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
      <div className="mx-auto max-w-5xl px-4 py-12">
        <Breadcrumb
          items={[
            { label: "Cobertura", href: "/coverage" },
            { label: "Detalhe da Execucao" },
          ]}
        />
        <div className="mt-6">
          <EmptyState
            icon={AlertTriangle}
            title="Erro ao carregar execucao"
            description={error ?? "Detalhe da execucao indisponivel."}
          />
          <div className="mt-4 text-center">
            <button
              onClick={fetchDetail}
              className="inline-flex items-center gap-1.5 rounded-lg bg-gov-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-gov-blue-700"
            >
              <RefreshCw className="h-4 w-4" />
              Tentar novamente
            </button>
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
    <div className="mx-auto max-w-5xl px-4 py-8">
      <Breadcrumb
        items={[
          { label: "Cobertura", href: "/coverage" },
          {
            label: `${detail.run.connector} / ${detail.run.job}`,
          },
        ]}
      />

      {/* Back link */}
      <Link
        href="/coverage"
        className="mt-3 inline-flex items-center gap-1 text-xs text-gov-gray-500 transition hover:text-gov-blue-600"
      >
        <ArrowLeft className="h-3 w-3" />
        Voltar para Cobertura
      </Link>

      {/* ── Header ─────────────────────────────────────────────── */}
      <section className="mt-4 rounded-lg border border-gov-gray-200 bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gov-blue-100">
                <Database className="h-5 w-5 text-gov-blue-700" />
              </div>
              <div>
                <h1 className="text-xl font-bold tracking-tight text-gov-gray-900">
                  {detail.run.connector} / {detail.run.job}
                </h1>
                {detail.job.domain && (
                  <span className="mt-0.5 inline-block rounded bg-gov-gray-100 px-1.5 py-0.5 text-xs text-gov-gray-600">
                    Dominio: {detail.job.domain}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs text-gov-gray-500">
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
        <div className="mt-3 flex items-start gap-2 rounded-md bg-gov-gray-50 px-3 py-2">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-gov-blue-500" />
          <p className="text-xs text-gov-gray-600">{statusCfg.desc}</p>
        </div>

        {/* Job description */}
        {detail.job.description && (
          <p className="mt-3 text-sm text-gov-gray-600">{detail.job.description}</p>
        )}
      </section>

      {/* ── KPI Grid ───────────────────────────────────────────── */}
      <section className="mt-6">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
          <BarChart3 className="h-5 w-5 text-gov-blue-600" />
          Numeros da Execucao
        </h2>
        <p className="mt-1 text-xs text-gov-gray-500">
          Metricas quantitativas do processamento. O pipeline busca dados brutos na fonte,
          normaliza para o modelo canonico e persiste com deduplicacao automatica.
        </p>

        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <KpiCard
            icon={Database}
            label="Itens Buscados"
            value={detail.run.items_fetched}
            tooltip="Quantidade de registros brutos recuperados da fonte de dados original durante esta execucao."
          />
          <KpiCard
            icon={ArrowDownUp}
            label="Itens Normalizados"
            value={detail.run.items_normalized}
            sub={`${normalizedPct}% do total buscado`}
            tooltip="Registros que foram convertidos para o formato padrao da plataforma. Uma taxa abaixo de 100% pode indicar registros com formato inesperado."
          />
          <KpiCard
            icon={Hash}
            label="Registros Persistidos"
            value={detail.summary.records_stored}
            sub={`${formatNumber(detail.summary.distinct_raw_ids)} IDs unicos`}
            tooltip="Total de registros salvos no banco de dados. IDs unicos indica quantos registros distintos foram identificados."
          />
          <KpiCard
            icon={Copy}
            label="Duplicidades Detectadas"
            value={detail.summary.duplicate_raw_ids}
            sub={dupPct > 0 ? `${dupPct}% do total` : "Nenhuma duplicidade"}
            tooltip="Registros que ja existiam no banco de dados. Um numero alto indica atualizacoes incrementais (normal) ou reprocessamento."
          />
        </div>
      </section>

      {/* ── Timeline ───────────────────────────────────────────── */}
      <section className="mt-6">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
          <Clock className="h-5 w-5 text-gov-blue-600" />
          Linha do Tempo
        </h2>
        <p className="mt-1 text-xs text-gov-gray-500">
          Janela temporal da execucao e dos registros processados.
        </p>

        <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
          <div className="rounded-lg border border-gov-gray-200 bg-white p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-gov-gray-500">
              Execucao
            </h3>
            <div className="mt-2 space-y-2 text-sm text-gov-gray-700">
              <div className="flex justify-between">
                <span className="text-gov-gray-500">Inicio</span>
                <span className="font-medium">{fmtMaybeDate(detail.run.started_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gov-gray-500">Fim</span>
                <span className="font-medium">{fmtMaybeDate(detail.run.finished_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gov-gray-500">Duracao</span>
                <span className="font-medium">{duration}</span>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-gov-gray-200 bg-white p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-gov-gray-500">
              Registros
            </h3>
            <div className="mt-2 space-y-2 text-sm text-gov-gray-700">
              <div className="flex justify-between">
                <span className="text-gov-gray-500">Registro mais antigo</span>
                <span className="font-medium">{fmtMaybeDate(detail.summary.first_record_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gov-gray-500">Registro mais recente</span>
                <span className="font-medium">{fmtMaybeDate(detail.summary.last_record_at)}</span>
              </div>
              {detail.run.cursor_start && (
                <div className="flex justify-between">
                  <span className="text-gov-gray-500">Cursor inicio</span>
                  <span className="font-mono text-xs font-medium">{detail.run.cursor_start}</span>
                </div>
              )}
              {detail.run.cursor_end && (
                <div className="flex justify-between">
                  <span className="text-gov-gray-500">Cursor fim</span>
                  <span className="font-mono text-xs font-medium">{detail.run.cursor_end}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ── How it works ───────────────────────────────────────── */}
      <section className="mt-6 rounded-lg border border-gov-blue-100 bg-gov-blue-50/40 p-4">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-gov-gray-900">
          <Info className="h-4 w-4 text-gov-blue-600" />
          Como funciona este processamento?
        </h2>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="flex items-start gap-2">
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gov-blue-100 text-xs font-bold text-gov-blue-700">
              1
            </div>
            <div>
              <p className="text-xs font-semibold text-gov-gray-800">Ingestao</p>
              <p className="text-xs text-gov-gray-600">
                O conector acessa a fonte publica e baixa os registros brutos (payloads JSON).
              </p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gov-blue-100 text-xs font-bold text-gov-blue-700">
              2
            </div>
            <div>
              <p className="text-xs font-semibold text-gov-gray-800">Normalizacao</p>
              <p className="text-xs text-gov-gray-600">
                Os registros sao convertidos para o formato padrao, extraindo campos-chave.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gov-blue-100 text-xs font-bold text-gov-blue-700">
              3
            </div>
            <div>
              <p className="text-xs font-semibold text-gov-gray-800">Persistencia</p>
              <p className="text-xs text-gov-gray-600">
                Registros unicos sao salvos; duplicatas sao detectadas automaticamente pelo ID.
              </p>
            </div>
          </div>
        </div>
        <p className="mt-3 text-xs text-gov-gray-500">
          O perfil de campos abaixo foi calculado sobre{" "}
          <strong>{detail.summary.profile_sampled_records}</strong> registro(s) desta execucao
          (limite tecnico: {detail.summary.profile_sample_limit}).
          {detail.job.supports_incremental && (
            <> Este job suporta ingestao incremental — apenas registros novos sao processados a cada execucao.</>
          )}
        </p>
      </section>

      {/* ── Errors (if any) ────────────────────────────────────── */}
      {detail.run.errors && Object.keys(detail.run.errors).length > 0 && (
        <section className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-red-800">
            <CircleX className="h-4 w-4" />
            Erros registrados
          </h2>
          <pre className="mt-2 max-h-40 overflow-auto rounded-md bg-white p-3 font-mono text-xs text-red-700">
            {stringifyJson(detail.run.errors)}
          </pre>
        </section>
      )}

      {/* ── Field Profile ──────────────────────────────────────── */}
      {detail.field_profile.length > 0 && (
        <section className="mt-6 rounded-lg border border-gov-gray-200 bg-white">
          <button
            type="button"
            onClick={() => setFieldProfileOpen((o) => !o)}
            className="flex w-full items-center justify-between gap-3 p-5 text-left"
          >
            <div>
              <h2 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
                <Braces className="h-5 w-5 text-gov-blue-600" />
                Perfil dos Campos ({detail.field_profile.length})
              </h2>
              <p className="mt-1 text-xs text-gov-gray-500">
                Presenca e tipos de cada campo encontrado nos registros brutos.
                A barra de cobertura indica em quantos registros o campo aparece.
              </p>
            </div>
            {fieldProfileOpen ? (
              <ChevronUp className="h-5 w-5 shrink-0 text-gov-gray-400" />
            ) : (
              <ChevronDown className="h-5 w-5 shrink-0 text-gov-gray-400" />
            )}
          </button>

          {fieldProfileOpen && (
            <div className="border-t border-gov-gray-200 px-5 pb-5 pt-3">
              <div className="overflow-x-auto rounded-lg border border-gov-gray-200">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-gov-gray-200 bg-gov-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-xs font-semibold text-gov-gray-600">
                        Campo
                      </th>
                      <th className="px-3 py-2 text-xs font-semibold text-gov-gray-600">
                        Cobertura
                      </th>
                      <th className="px-3 py-2 text-xs font-semibold text-gov-gray-600">
                        Tipo(s)
                      </th>
                      <th className="px-3 py-2 text-xs font-semibold text-gov-gray-600">
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
              <p className="mt-2 text-xs text-gov-gray-400">
                Cobertura indica a proporcao de registros amostrados que possuem este campo preenchido.
                Verde ({"\u2265"}90%), amarelo (50-89%), vermelho ({"<"}50%).
              </p>
            </div>
          )}
        </section>
      )}

      {/* ── Samples ────────────────────────────────────────────── */}
      <section className="mt-6 rounded-lg border border-gov-gray-200 bg-white">
        <button
          type="button"
          onClick={() => setSamplesSectionOpen((o) => !o)}
          className="flex w-full items-center justify-between gap-3 p-5 text-left"
        >
          <div>
            <h2 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
              <FileJson className="h-5 w-5 text-gov-blue-600" />
              Amostra de Registros ({detail.samples.length})
            </h2>
            <p className="mt-1 text-xs text-gov-gray-500">
              Registros reais processados nesta execucao, exibidos para auditoria e verificacao.
              Cada registro mostra os principais campos e permite ver o JSON bruto original.
            </p>
          </div>
          {samplesSectionOpen ? (
            <ChevronUp className="h-5 w-5 shrink-0 text-gov-gray-400" />
          ) : (
            <ChevronDown className="h-5 w-5 shrink-0 text-gov-gray-400" />
          )}
        </button>

        {samplesSectionOpen && (
          <div className="border-t border-gov-gray-200 px-5 pb-5 pt-3">
            {detail.samples.length === 0 ? (
              <div className="rounded-lg border border-gov-gray-200 bg-gov-gray-50 p-6 text-center">
                <FileText className="mx-auto h-8 w-8 text-gov-gray-300" />
                <p className="mt-2 text-sm text-gov-gray-500">
                  Nenhum registro bruto encontrado para esta execucao.
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
                        className="rounded-lg border border-gov-gray-200 bg-white p-4"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className="flex h-6 w-6 items-center justify-center rounded bg-gov-gray-100 text-xs font-bold text-gov-gray-600">
                              {gIdx + 1}
                            </span>
                            <p className="font-mono text-xs font-semibold text-gov-gray-800">
                              {sample.raw_id}
                            </p>
                          </div>
                          <p className="text-xs text-gov-gray-500">
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
                                className="rounded-md border border-gov-gray-100 bg-gov-gray-50 px-2.5 py-2"
                              >
                                <p className="text-[11px] font-semibold uppercase tracking-wide text-gov-gray-400">
                                  {key}
                                </p>
                                {blockRender ? (
                                  <pre className="mt-1 max-h-48 overflow-auto rounded bg-white px-2 py-1.5 font-mono text-[11px] leading-relaxed text-gov-gray-700 whitespace-pre-wrap break-words">
                                    {displayValue}
                                  </pre>
                                ) : (
                                  <p className="mt-0.5 text-xs text-gov-gray-700 break-words">
                                    {displayValue}
                                  </p>
                                )}
                              </div>
                            );
                          })}
                        </div>

                        <details
                          className="mt-3 rounded-md border border-gov-gray-200"
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
                          <summary className="cursor-pointer rounded-t-md bg-gov-gray-50 px-3 py-2 text-xs font-medium text-gov-gray-600 hover:text-gov-gray-800">
                            Ver JSON bruto original
                          </summary>
                          <pre className="max-h-72 overflow-auto border-t border-gov-gray-200 bg-gov-gray-50 p-3 text-[11px] text-gov-gray-700">
                            {stringifyJson(sample.raw_data)}
                          </pre>
                        </details>
                      </article>
                    );
                  })}
                </div>

                {totalPages > 1 && (
                  <div className="mt-4 flex items-center justify-between">
                    <p className="text-xs text-gov-gray-500">
                      {globalOffset + 1}–{Math.min(globalOffset + SAMPLES_PER_PAGE, detail.samples.length)} de {detail.samples.length} registros
                    </p>
                    <div className="flex items-center gap-1">
                      <button
                        disabled={samplesPage === 0}
                        onClick={() => setSamplesPage((p) => p - 1)}
                        className="rounded-md border border-gov-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gov-gray-700 hover:bg-gov-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
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
                                ? "border-gov-blue-600 bg-gov-blue-600 text-white"
                                : "border-gov-gray-200 bg-white text-gov-gray-700 hover:bg-gov-gray-50"
                            }`}
                          >
                            {i + 1}
                          </button>
                        ))
                      ) : (
                        <span className="px-2 text-xs text-gov-gray-500">
                          {samplesPage + 1} / {totalPages}
                        </span>
                      )}
                      <button
                        disabled={samplesPage === totalPages - 1}
                        onClick={() => setSamplesPage((p) => p + 1)}
                        className="rounded-md border border-gov-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gov-gray-700 hover:bg-gov-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        Proximo
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
      <div className="mt-6 rounded-lg border border-gov-gray-100 bg-gov-gray-50 p-3">
        <p className="text-xs text-gov-gray-500">
          <strong>Transparencia:</strong> Esta pagina exibe o detalhe tecnico de uma
          execucao de ingestao de dados publicos. Os registros sao obtidos exclusivamente
          de fontes oficiais (portais de transparencia, APIs publicas) e tratados com
          deduplicacao automatica. Nenhum dado pessoal e coletado alem do estritamente
          necessario para fins de controle social e interesse publico (LGPD, art. 7, VII).
        </p>
      </div>
    </div>
  );
}
